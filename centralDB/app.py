import json
import os
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, jsonify, request


app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_PATH = os.path.join(DATA_DIR, "logs.json")
LOCK = Lock()

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

FILTER_FIELDS = {"tenant_id", "region_id", "operation_type", "synced"}


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


def _apply_filters(logs, args):
    filtered = logs
    for field in FILTER_FIELDS:
        value = args.get(field)
        if value is None:
            continue
        if field == "synced":
            want_synced = value.lower() == "true"
            filtered = [log for log in filtered if log.get("synced") is want_synced]
        else:
            filtered = [log for log in filtered if str(log.get(field)) == value]
    return filtered


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/central/logs", methods=["POST"])
def ingest_log():
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
        log_entry["received_at"] = _utc_now()
        logs.append(log_entry)
        _save_logs(logs)

    return jsonify({"status": "stored", "log_id": log_entry["log_id"]}), 201


@app.route("/central/logs/batch", methods=["POST"])
def ingest_batch():
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
            log_entry["received_at"] = _utc_now()
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


@app.route("/central/logs", methods=["GET"])
def list_logs():
    with LOCK:
        logs = _load_logs()
    filtered = _apply_filters(logs, request.args)
    return jsonify({"count": len(filtered), "logs": filtered})


@app.route("/central/reports/summary", methods=["GET"])
def summary():
    with LOCK:
        logs = _load_logs()

    by_operation = {}
    by_tenant = {}
    for log in logs:
        operation_type = log.get("operation_type")
        tenant_id = log.get("tenant_id")
        by_operation[operation_type] = by_operation.get(operation_type, 0) + 1
        by_tenant[tenant_id] = by_tenant.get(tenant_id, 0) + 1

    return jsonify({"count": len(logs), "by_operation_type": by_operation, "by_tenant_id": by_tenant})


if __name__ == "__main__":
    _ensure_data_file()
    app.run(host="0.0.0.0", port=5001)
