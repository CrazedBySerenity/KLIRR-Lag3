import os
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CENTRAL_DIR = os.path.join(ROOT_DIR, "centralDB")
NODE_DIR = os.path.join(ROOT_DIR, "asyncSyncing")

CENTRAL_URL = "http://localhost:5001/health"
NODE_URL = "http://localhost:5000/health"


def log(message):
    print(f"[demo] {message}", flush=True)


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


def run_smoke_test(path, label):
    log(f"Running {label} smoke test...")
    result = subprocess.run(
        [sys.executable, path],
        cwd=os.path.dirname(path),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{label} smoke test failed")
    log(f"{label} smoke test passed.")


def main():
    central_app = os.path.join(CENTRAL_DIR, "app.py")
    node_app = os.path.join(NODE_DIR, "app.py")
    central_smoke = os.path.join(CENTRAL_DIR, "smoke_test.py")
    node_smoke = os.path.join(NODE_DIR, "smoke_test.py")

    log("Starting Central DB service...")
    central_proc = subprocess.Popen([sys.executable, central_app], cwd=CENTRAL_DIR)
    try:
        if not wait_for_health(CENTRAL_URL):
            raise RuntimeError("Central DB health check failed")
        log("Central DB is healthy.")

        log("Starting Node service...")
        env = os.environ.copy()
        env["CENTRAL_DB_URL"] = "http://localhost:5001"
        node_proc = subprocess.Popen([sys.executable, node_app], cwd=NODE_DIR, env=env)
        try:
            if not wait_for_health(NODE_URL):
                raise RuntimeError("Node health check failed")
            log("Node is healthy.")

            run_smoke_test(node_smoke, "Node")
            run_smoke_test(central_smoke, "Central DB")

            log("Demo complete.")
        finally:
            log("Stopping Node service...")
            node_proc.terminate()
            node_proc.wait(timeout=5)
    finally:
        log("Stopping Central DB service...")
        central_proc.terminate()
        central_proc.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"Demo failed: {exc}")
        sys.exit(1)
