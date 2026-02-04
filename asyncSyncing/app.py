import json
import os
from datetime import datetime, timezone
from threading import Lock

import requests
from flask import Flask, jsonify, request


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_PATH = os.environ.get("LOGS_PATH")
if LOGS_PATH:
    DATA_DIR = os.path.dirname(LOGS_PATH)
else:
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    LOGS_PATH = os.path.join(DATA_DIR, "logs.json")
LOCK = Lock()
CENTRAL_DB_URL = os.environ.get("CENTRAL_DB_URL", "http://localhost:5001").rstrip("/")
CENTRAL_DB_TIMEOUT = float(os.environ.get("CENTRAL_DB_TIMEOUT", "5"))
CENTRAL_DB_BATCH_SIZE = int(os.environ.get("CENTRAL_DB_BATCH_SIZE", "50"))

REQUIRED_FIELDS = [
    "log_id",
    "op_id",
    "idempotency_key",
    "source_node_id",
    "target_scope",
    "operation_type",
    "operation_body",
    "occurred_at",
    "recorded_at",
    "actor_type",
    "actor_id",
    "tenant_id",
    "location_id",
    "region_id",
    "facility_id",
    "retries",
]

CENTRAL_REQUIRED_FIELDS = [
    "facility_id",
    "tenant_id",
    "region_id",
    "operation_type",
    "idempotency_key",
]


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(LOGS_PATH):
        with open(LOGS_PATH, "w", encoding="utf-8") as handle:
            json.dump([], handle, ensure_ascii=False, indent=2)


def _load_logs():
    _ensure_data_file()
    with open(LOGS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_logs(logs):
    with open(LOGS_PATH, "w", encoding="utf-8") as handle:
        json.dump(logs, handle, ensure_ascii=False, indent=2)


def _validate_payload(payload):
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        return False, f"Missing fields: {', '.join(missing)}"
    if not isinstance(payload.get("retries"), int):
        return False, "Field retries must be an integer"
    return True, ""


def _find_by_idempotency(logs, idempotency_key):
    for log in logs:
        if log.get("idempotency_key") == idempotency_key:
            return log
    return None


def _missing_central_fields(log_entry):
    return [field for field in CENTRAL_REQUIRED_FIELDS if not log_entry.get(field)]


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/logs", methods=["POST"])
def create_log():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    is_valid, error = _validate_payload(payload)
    if not is_valid:
        return jsonify({"error": error}), 400

    with LOCK:
        logs = _load_logs()
        existing = _find_by_idempotency(logs, payload["idempotency_key"])
        if existing is not None:
            return (
                jsonify(
                    {
                        "error": "Duplicate idempotency_key",
                        "existing_log_id": existing.get("log_id"),
                    }
                ),
                409,
            )

        log_entry = dict(payload)
        log_entry["created_at"] = _utc_now()
        log_entry["synced"] = False
        log_entry["synced_at"] = None
        logs.append(log_entry)
        _save_logs(logs)

    return jsonify({"status": "stored", "log_id": log_entry["log_id"]}), 201


@app.route("/logs", methods=["GET"])
def list_logs():
    synced_param = request.args.get("synced")
    with LOCK:
        logs = _load_logs()

    if synced_param is not None:
        want_synced = synced_param.lower() == "true"
        logs = [log for log in logs if log.get("synced") is want_synced]

    return jsonify({"count": len(logs), "logs": logs})


@app.route("/node/logs/batch", methods=["POST"])
def ingest_node_batch():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not isinstance(payload, list):
        return jsonify({"error": "Expected a JSON array"}), 400

    results = []
    accepted = 0
    duplicates = 0
    errors = 0

    with LOCK:
        logs = _load_logs()
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                results.append(
                    {"index": index, "status": "error", "error": "Item must be object"}
                )
                errors += 1
                continue

            is_valid, error = _validate_payload(item)
            if not is_valid:
                results.append({"index": index, "status": "error", "error": error})
                errors += 1
                continue

            existing = _find_by_idempotency(logs, item["idempotency_key"])
            if existing is not None:
                results.append(
                    {
                        "index": index,
                        "status": "duplicate",
                        "existing_log_id": existing.get("log_id"),
                        "idempotency_key": item["idempotency_key"],
                    }
                )
                duplicates += 1
                continue

            log_entry = dict(item)
            log_entry["created_at"] = _utc_now()
            log_entry["synced"] = False
            log_entry["synced_at"] = None
            logs.append(log_entry)
            results.append(
                {
                    "index": index,
                    "status": "accepted",
                    "log_id": log_entry.get("log_id"),
                    "idempotency_key": log_entry.get("idempotency_key"),
                }
            )
            accepted += 1

        _save_logs(logs)

    return jsonify(
        {
            "accepted": accepted,
            "duplicates": duplicates,
            "errors": errors,
            "results": results,
        }
    )


@app.route("/sync/run", methods=["POST"])
def run_sync():
    with LOCK:
        logs = _load_logs()
        updated = 0
        now = _utc_now()
        for log in logs:
            if not log.get("synced"):
                log["synced"] = True
                log["synced_at"] = now
                updated += 1
        _save_logs(logs)

    return jsonify({"synced": updated})


@app.route("/sync/central", methods=["POST"])
def sync_central():
    with LOCK:
        logs = _load_logs()
        unsynced = [(index, log) for index, log in enumerate(logs) if not log.get("synced")]

        if not unsynced:
            return jsonify({"pushed": 0, "synced": 0, "duplicates": 0, "errors": 0})

        batch = []
        batch_indexes = []
        errors = 0
        for index, log in unsynced[:CENTRAL_DB_BATCH_SIZE]:
            missing = _missing_central_fields(log)
            if missing:
                log["retries"] = int(log.get("retries", 0)) + 1
                errors += 1
                continue
            batch.append(log)
            batch_indexes.append(index)

        if not batch:
            _save_logs(logs)
            return jsonify({"pushed": 0, "synced": 0, "duplicates": 0, "errors": errors})

    if len(batch) == 1:
        log_index = batch_indexes[0]
        try:
            response = requests.post(
                f"{CENTRAL_DB_URL}/central/logs",
                json=batch[0],
                timeout=CENTRAL_DB_TIMEOUT,
            )
        except requests.RequestException as exc:
            with LOCK:
                logs = _load_logs()
                logs[log_index]["retries"] = int(logs[log_index].get("retries", 0)) + 1
                _save_logs(logs)
            return jsonify({"error": str(exc)}), 502

        if response.status_code == 201:
            logs[log_index]["synced"] = True
            logs[log_index]["synced_at"] = _utc_now()
            synced = 1
            duplicates = 0
        elif response.status_code == 409:
            logs[log_index]["synced"] = True
            logs[log_index]["synced_at"] = _utc_now()
            synced = 0
            duplicates = 1
        else:
            with LOCK:
                logs = _load_logs()
                logs[log_index]["retries"] = int(logs[log_index].get("retries", 0)) + 1
                _save_logs(logs)
            return jsonify({"error": "Central DB error", "status": response.status_code}), 502
    else:
        try:
            response = requests.post(
                f"{CENTRAL_DB_URL}/central/logs/batch",
                json=batch,
                timeout=CENTRAL_DB_TIMEOUT,
            )
        except requests.RequestException as exc:
            with LOCK:
                logs = _load_logs()
                for index in batch_indexes:
                    logs[index]["retries"] = int(logs[index].get("retries", 0)) + 1
                _save_logs(logs)
            return jsonify({"error": str(exc)}), 502

        if response.status_code != 200:
            with LOCK:
                logs = _load_logs()
                for index in batch_indexes:
                    logs[index]["retries"] = int(logs[index].get("retries", 0)) + 1
                _save_logs(logs)
            return jsonify({"error": "Central DB error", "status": response.status_code}), 502

        payload = response.json()
        results = payload.get("results", [])
        synced = 0
        duplicates = 0
        for result in results:
            result_index = result.get("index")
            if result_index is None or result_index >= len(batch_indexes):
                errors += 1
                continue
            log_index = batch_indexes[result_index]
            status = result.get("status")
            if status in {"accepted", "duplicate"}:
                logs[log_index]["synced"] = True
                logs[log_index]["synced_at"] = _utc_now()
                if status == "duplicate":
                    duplicates += 1
                else:
                    synced += 1
            else:
                logs[log_index]["retries"] = int(logs[log_index].get("retries", 0)) + 1
                errors += 1

    with LOCK:
        _save_logs(logs)

    return jsonify(
        {
            "pushed": len(batch),
            "synced": synced,
            "duplicates": duplicates,
            "errors": errors,
        }
    )


if __name__ == "__main__":
    _ensure_data_file()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
