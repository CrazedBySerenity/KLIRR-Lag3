import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CENTRAL_DIR = os.path.join(ROOT_DIR, "centralDB")
NODE_DIR = os.path.join(ROOT_DIR, "asyncSyncing")
NODE_APP = os.path.join(NODE_DIR, "app.py")

CENTRAL_BASE_URL = "http://localhost:5001"
NODE_A_PORT = 5000
NODE_B_PORT = 5002
NODE_A_URL = f"http://localhost:{NODE_A_PORT}"
NODE_B_URL = f"http://localhost:{NODE_B_PORT}"
CENTRAL_HEALTH = f"{CENTRAL_BASE_URL}/health"
NODE_A_HEALTH = f"{NODE_A_URL}/health"
NODE_B_HEALTH = f"{NODE_B_URL}/health"
CENTRAL_OFFLINE_URL = "http://localhost:5999"

START_TIME = time.perf_counter()
STEP_COUNTER = 0
STEP_DELAY = float(os.environ.get("DEMO_STEP_DELAY", "1.0"))
STAGE_DELAY = float(os.environ.get("DEMO_STAGE_DELAY", "10.0"))


def stamp():
    elapsed = int(time.perf_counter() - START_TIME)
    minutes = elapsed // 60
    seconds = elapsed % 60
    return f"{minutes:02d}:{seconds:02d}"


def stage(title, body):
    header = f"[{stamp()}] {title}"
    body_lines = [line.strip() for line in body.splitlines() if line.strip()]
    width = max([len(header)] + [len(line) for line in body_lines] + [48])
    divider = "-" * width

    time.sleep(STAGE_DELAY)
    clear_console()
    print("", flush=True)
    print(divider, flush=True)
    print("", flush=True)
    print(header, flush=True)
    for line in body_lines:
        print(line, flush=True)
    print("", flush=True)
    print(divider, flush=True)
    print("", flush=True)
    time.sleep(STAGE_DELAY)


def step(text, delay=None):
    global STEP_COUNTER
    STEP_COUNTER += 1
    if delay is None:
        delay = STEP_DELAY
    print(f"  {STEP_COUNTER:02d}. {text}", flush=True)
    print("", flush=True)
    time.sleep(delay)


def wait_for_health(url, timeout_seconds=15):
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except URLError:
            pass
        time.sleep(0.5)
    return False


def request_json(method, url, payload=None, timeout=4):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return exc.code, parsed
    except URLError as exc:
        return None, {"error": str(exc)}


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def build_log(source_node_id, id_suffix, amount):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "log_id": f"log-{id_suffix}",
        "op_id": f"op-{id_suffix}",
        "idempotency_key": f"idem-{id_suffix}",
        "source_node_id": source_node_id,
        "target_scope": "central",
        "operation_type": "record_transaction",
        "operation_body": {"amount": amount},
        "occurred_at": now,
        "recorded_at": now,
        "actor_type": "system",
        "actor_id": "demo",
        "tenant_id": "municipality-1",
        "location_id": "location-1",
        "region_id": "region-1",
        "facility_id": "facility-1",
        "retries": 0,
    }


def start_node(port, data_dir, central_url):
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["DATA_DIR"] = data_dir
    env["CENTRAL_DB_URL"] = central_url
    return subprocess.Popen([sys.executable, NODE_APP], cwd=NODE_DIR, env=env)


def stop_process(proc, label):
    if proc is None:
        return
    step(f"Stopping {label}...")
    proc.terminate()
    proc.wait(timeout=5)


def main():
    central_app = os.path.join(CENTRAL_DIR, "app.py")
    node_a_data = os.path.join(NODE_DIR, "data", "node-a")
    node_b_data = os.path.join(NODE_DIR, "data", "node-b")

    stage(
        "Boot services",
        "We are bringing up the central database and two field nodes.\n"
        "In a real deployment these would be separate sites with intermittent connectivity.",
    )
    step("Starting Central DB...")
    central_proc = subprocess.Popen([sys.executable, central_app], cwd=CENTRAL_DIR)
    node_a_proc = None
    node_b_proc = None
    try:
        if not wait_for_health(CENTRAL_HEALTH):
            raise RuntimeError("Central DB health check failed")
        step("Central DB is healthy")

        step("Starting Node A (central link down)")
        node_a_proc = start_node(NODE_A_PORT, node_a_data, CENTRAL_OFFLINE_URL)
        if not wait_for_health(NODE_A_HEALTH):
            raise RuntimeError("Node A health check failed")
        step("Node A is healthy")

        step("Starting Node B")
        node_b_proc = start_node(NODE_B_PORT, node_b_data, CENTRAL_BASE_URL)
        if not wait_for_health(NODE_B_HEALTH):
            raise RuntimeError("Node B health check failed")
        step("Node B is healthy")
        clear_console()

        stage(
            "Create local activity",
            "Each node records its own operational logs locally first.\n"
            "This mimics field activity during a disruption where central access is unreliable.",
        )
        log_a = build_log("node-a", uuid.uuid4().hex[:8], amount=5)
        log_b = build_log("node-b", uuid.uuid4().hex[:8], amount=2)

        step("Posting one log to Node A")
        status, body = request_json("POST", f"{NODE_A_URL}/logs", log_a)
        step(f"Node A stored log (status {status})")

        step("Posting one log to Node B")
        status, body = request_json("POST", f"{NODE_B_URL}/logs", log_b)
        step(f"Node B stored log (status {status})")

        stage(
            "Local unsynced view",
            "We check local backlogs before any sync happens.\n"
            "These counts show what still needs to be pushed upstream.",
        )
        status, body = request_json("GET", f"{NODE_A_URL}/logs?synced=false")
        step(f"Node A unsynced: {body.get('count', 0)}")
        status, body = request_json("GET", f"{NODE_B_URL}/logs?synced=false")
        step(f"Node B unsynced: {body.get('count', 0)}")

        stage(
            "Central cutout",
            "Node A attempts to reach the central database, but the link drops at the worst time.\n"
            "We expect this sync attempt to fail and continue with a fallback plan.",
        )
        step("Node A attempts to sync to central")
        try:
            status, body = request_json("POST", f"{NODE_A_URL}/sync/central")
        except Exception as exc:
            status, body = None, {"error": str(exc)}
        if status == 200:
            step("Unexpected success; check central cutout settings")
        else:
            error_message = (
                body.get("error", "sync failed") if isinstance(body, dict) else "sync failed"
            )
            step(f"Expected failure: {error_message}")

        stage(
            "Failover to sibling",
            "Node A forwards its unsynced logs to a nearby sibling node.\n"
            "This models a local relay when the direct path to central is unavailable.",
        )
        step("Fetching Node A unsynced logs")
        status, body = request_json("GET", f"{NODE_A_URL}/logs?synced=false")
        logs_to_forward = body.get("logs", []) if status == 200 else []
        step(f"Forwarding {len(logs_to_forward)} logs to Node B")
        status, body = request_json(
            "POST", f"{NODE_B_URL}/node/logs/batch", logs_to_forward
        )
        step(
            f"Node B accepted {body.get('accepted', 0)}, duplicates {body.get('duplicates', 0)}"
        )

        stage(
            "Sibling sync succeeds",
            "Node B now has both its own logs and Node A's forwarded logs.\n"
            "It syncs to central once connectivity is available.",
        )
        step("Node B syncs to central")
        status, body = request_json("POST", f"{NODE_B_URL}/sync/central")
        step(
            f"Node B result: synced {body.get('synced', 0)}, duplicates {body.get('duplicates', 0)}, errors {body.get('errors', 0)}"
        )

        stage(
            "Node A restart + retry",
            "Node A comes back online with a working link to central.\n"
            "A retry should be safe because the central database is idempotent.",
        )
        stop_process(node_a_proc, "Node A")
        step("Restarting Node A with working central URL")
        node_a_proc = start_node(NODE_A_PORT, node_a_data, CENTRAL_BASE_URL)
        if not wait_for_health(NODE_A_HEALTH):
            raise RuntimeError("Node A health check failed after restart")
        step("Node A is healthy")

        step("Node A retries sync")
        status, body = request_json("POST", f"{NODE_A_URL}/sync/central")
        step(
            f"Node A result: synced {body.get('synced', 0)}, duplicates {body.get('duplicates', 0)}, errors {body.get('errors', 0)}"
        )

        stage(
            "Central view",
            "We inspect the central database to confirm all logs arrived.\n"
            "Summary metrics show the system converged despite outages.",
        )
        status, body = request_json("GET", f"{CENTRAL_BASE_URL}/central/logs")
        step(f"Central total logs: {body.get('count', 0)}")
        status, body = request_json("GET", f"{CENTRAL_BASE_URL}/central/reports/summary")
        step(f"Central by operation: {body.get('by_operation_type', {})}")
        step(f"Central by tenant: {body.get('by_tenant_id', {})}")

        step("Demo complete.")
    finally:
        try:
            stop_process(node_b_proc, "Node B")
        except Exception:
            pass
        try:
            stop_process(node_a_proc, "Node A")
        except Exception:
            pass
        stop_process(central_proc, "Central DB")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[{stamp()}] Demo failed: {exc}", flush=True)
        sys.exit(1)
