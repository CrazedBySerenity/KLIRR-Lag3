# Async Syncing PoC (Flask)

Minimal Flask backend that stores async sync logs in a JSON file and simulates
syncing "up the chain" for crisis-response municipal workflows.

## Quick start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python app.py
```

Server runs on `http://localhost:5000`.

## Endpoints

- `GET /health` — liveness check.
- `POST /logs` — store a log entry.
- `GET /logs` — list logs. Use `?synced=true|false` to filter.
- `POST /sync/run` — mark unsynced logs as synced.

## Log body fields

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
  "retries": 0
}
```

## Curl examples

```bash
curl -s http://localhost:5000/health
```

```bash
curl -s -X POST http://localhost:5000/logs \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "log-1",
    "op_id": "op-1",
    "idempotency_key": "idem-1",
    "source_node_id": "node-1",
    "target_scope": "level-2",
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
    "retries": 0
  }'
```

```bash
curl -s http://localhost:5000/logs
```

```bash
curl -s -X POST http://localhost:5000/sync/run
```
