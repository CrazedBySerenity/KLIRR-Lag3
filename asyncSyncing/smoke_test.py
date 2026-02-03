import json
import sys
from datetime import datetime, timezone

import requests


BASE_URL = "http://localhost:5000"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    health = requests.get(f"{BASE_URL}/health", timeout=5)
    health.raise_for_status()

    payload = {
        "log_id": "smoke-log-1",
        "op_id": "smoke-op-1",
        "idempotency_key": "smoke-idem-1",
        "source_node_id": "node-1",
        "target_scope": "level-2",
        "operation_type": "record_transaction",
        "operation_body": {"amount": 1},
        "occurred_at": utc_now(),
        "recorded_at": utc_now(),
        "actor_type": "system",
        "actor_id": "smoke-script",
        "tenant_id": "municipality-1",
        "location_id": "location-1",
        "region_id": "region-1",
        "facility_id": "facility-1",
        "retries": 0,
    }

    create = requests.post(
        f"{BASE_URL}/logs",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    create.raise_for_status()

    before = requests.get(f"{BASE_URL}/logs?synced=false", timeout=5)
    before.raise_for_status()

    sync = requests.post(f"{BASE_URL}/sync/run", timeout=5)
    sync.raise_for_status()

    after = requests.get(f"{BASE_URL}/logs?synced=true", timeout=5)
    after.raise_for_status()

    print("Smoke test passed.")
    print("Unsynced logs:", before.json().get("count"))
    print("Synced logs:", after.json().get("count"))


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"Smoke test failed: {exc}")
        sys.exit(1)
