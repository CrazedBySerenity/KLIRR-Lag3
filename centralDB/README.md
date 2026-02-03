# Central DB PoC (Flask)

Standalone central database service that ingests logs from nodes and provides
basic query/reporting endpoints. Data is stored in a JSON file.

## Quick start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python app.py
```

Server runs on `http://localhost:5001`.

## Endpoints

- `GET /health` — liveness check.
- `POST /central/logs` — ingest a single log entry.
- `POST /central/logs/batch` — ingest a list of log entries; returns per‑item status.
- `GET /central/logs` — list logs with filters: `tenant_id`, `region_id`, `operation_type`, `synced`.
- `GET /central/reports/summary` — totals by operation type and tenant.

## Log body fields

Same schema as `asyncSyncing`:

```json
{
  "log_id": "uuid",
  "op_id": "uuid",
  "idempotency_key": "string",
  "source_node_id": "uuid",
  "target_scope": "string",
  "operation_type": "record_transaction",
  "operation_body": { "any": "json" },
  "occurred_at": "2026-02-03T10:00:00Z",
  "recorded_at": "2026-02-03T10:00:00Z",
  "actor_type": "system",
  "actor_id": "string",
  "tenant_id": "municipality-id",
  "location_id": "string",
  "region_id": "string",
  "facility_id": "string",
  "retries": 0,
  "synced": false,
  "synced_at": null
}
```

## Idempotency

Duplicate `idempotency_key` returns HTTP 409 with `existing_log_id`.

## Curl examples

```bash
curl -s http://localhost:5001/health
```

```bash
curl -s -X POST http://localhost:5001/central/logs \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "log-1",
    "op_id": "op-1",
    "idempotency_key": "idem-1",
    "source_node_id": "node-1",
    "target_scope": "central",
    "operation_type": "record_transaction",
    "operation_body": { "amount": 5 },
    "occurred_at": "2026-02-03T10:00:00Z",
    "recorded_at": "2026-02-03T10:05:00Z",
    "actor_type": "system",
    "actor_id": "service-1",
    "tenant_id": "municipality-1",
    "location_id": "location-1",
    "region_id": "region-1",
    "facility_id": "facility-1",
    "retries": 0,
    "synced": false,
    "synced_at": null
  }'
```

```bash
curl -s -X POST http://localhost:5001/central/logs/batch \
  -H "Content-Type: application/json" \
  -d '[{ "log_id": "log-2", "op_id": "op-2", "idempotency_key": "idem-2", "source_node_id": "node-1", "target_scope": "central", "operation_type": "record_transaction", "operation_body": { "amount": 1 }, "occurred_at": "2026-02-03T10:00:00Z", "recorded_at": "2026-02-03T10:05:00Z", "actor_type": "system", "actor_id": "service-1", "tenant_id": "municipality-1", "location_id": "location-1", "region_id": "region-1", "facility_id": "facility-1", "retries": 0, "synced": false, "synced_at": null }]'
```
