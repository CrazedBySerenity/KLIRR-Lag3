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

    log_entry = dict(payload)
    log_entry["created_at"] = _utc_now()
    log_entry["synced"] = False
    log_entry["synced_at"] = None

    with LOCK:
        logs = _load_logs()
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


if __name__ == "__main__":
    _ensure_data_file()
    app.run(host="0.0.0.0", port=5000, debug=True)
