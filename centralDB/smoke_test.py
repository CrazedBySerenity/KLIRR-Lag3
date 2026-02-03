import json
import sys
from datetime import datetime, timezone

import requests


BASE_URL = "http://localhost:5001"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_payload(suffix):
    return {
        "log_id": f"central-log-{suffix}",
        "op_id": f"central-op-{suffix}",
        "idempotency_key": f"central-idem-{suffix}",
        "source_node_id": "node-1",
        "target_scope": "central",
        "operation_type": "record_transaction",
        "operation_body": {"amount": 1},
        "occurred_at": utc_now(),
        "recorded_at": utc_now(),
        "actor_type": "system",
        "actor_id": "central-smoke",
        "tenant_id": "municipality-1",
        "location_id": "location-1",
        "region_id": "region-1",
        "facility_id": "facility-1",
        "retries": 0,
        "synced": False,
        "synced_at": None,
    }


def main():
    health = requests.get(f"{BASE_URL}/health", timeout=5)
    health.raise_for_status()

    single = requests.post(
        f"{BASE_URL}/central/logs",
        data=json.dumps(make_payload("single")),
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    if single.status_code not in (201, 409):
        single.raise_for_status()

    batch_payload = [make_payload("batch-1"), make_payload("batch-2")]
    batch = requests.post(
        f"{BASE_URL}/central/logs/batch",
        data=json.dumps(batch_payload),
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    batch.raise_for_status()

    logs = requests.get(
        f"{BASE_URL}/central/logs?tenant_id=municipality-1", timeout=5
    )
    logs.raise_for_status()

    summary = requests.get(f"{BASE_URL}/central/reports/summary", timeout=5)
    summary.raise_for_status()

    print("Smoke test passed.")
    print("Logs count:", logs.json().get("count"))
    print("Summary:", summary.json().get("count"))


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        print(f"Smoke test failed: {exc}")
        sys.exit(1)
