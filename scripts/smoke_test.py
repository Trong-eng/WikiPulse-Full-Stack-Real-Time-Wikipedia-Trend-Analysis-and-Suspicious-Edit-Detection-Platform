"""Run a real isolated Kafka/Spark/Cassandra/API/Streamlit smoke demonstration."""

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def run_smoke(keep: bool = False, build: bool = True) -> dict:
    run_id = f"{datetime.now(timezone.utc):smoke-%Y%m%d%H%M%S}-{uuid4().hex}"
    project = f"wikipulse-{run_id}"
    env = dict(os.environ)
    env.update({
        "COMPOSE_PROJECT_NAME": project, "RUN_ID": run_id, "PIPELINE_MODE": "REPLAY",
        "API_HOST_PORT": "0", "DASHBOARD_HOST_PORT": "0", "KAFKA_HOST_PORT": "0",
        "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092", "CASSANDRA_HOST": "cassandra",
        "KAFKA_RAW_TOPIC": "wikipedia.recentchange.raw",
        "KAFKA_DLQ_TOPIC": "wikipedia.recentchange.dlq", "CASSANDRA_PORT": "9042",
        "CASSANDRA_KEYSPACE": "wikipulse", "DATA_BASE_PATH": "file:///data/wikipulse",
        "DASHBOARD_API_URL": "http://api:8000", "PIPELINE_VERSION": "0.1.0",
        "USER_HASH_SALT": "local-demo-change-me", "MAX_OFFSETS_PER_TRIGGER": "1000",
        "SPARK_CHECKPOINT_PATH": "/data/checkpoints", "TRIGGER_INTERVAL": "5 seconds",
        "WATERMARK_DELAY": "10 minutes", "WIKI_ALLOWLIST": "enwiki,viwiki",
    })
    # External Kafka listener is unused by smoke; advertise a valid container port.
    env["KAFKA_ADVERTISED_EXTERNAL_PORT"] = "19092"
    output_dir = ROOT / "artifacts" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    command = ["docker", "compose", "-p", project]

    def compose(*args: str, timeout: int = 300) -> str:
        result = subprocess.run(command + list(args), cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        with (output_dir / "commands.log").open("a", encoding="utf-8") as log:
            log.write(f"$ docker compose {' '.join(args)}\n{result.stdout}\n")
        if result.returncode:
            raise RuntimeError(f"Compose failed ({result.returncode}); see {output_dir}/commands.log")
        return result.stdout

    def get(url: str) -> dict | str:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body

    def wait_for(check, label: str, timeout: int = 180):
        deadline = time.monotonic() + timeout
        last = "not ready"
        while time.monotonic() < deadline:
            try:
                value = check()
                if value:
                    return value
            except (OSError, ValueError, RuntimeError) as exc:
                last = str(exc)
            time.sleep(3)
        raise RuntimeError(f"Timed out waiting for {label}: {last}")

    report = {"project": project, "run_id": run_id, "status": "failed"}
    try:
        if build:
            compose("build", "api", "spark", "dashboard", "replay", timeout=1200)
        compose("up", "-d", "api", "spark", "dashboard", timeout=360)
        api_port = compose("port", "api", "8000").strip().rsplit(":", 1)[1]
        ui_port = compose("port", "dashboard", "8501").strip().rsplit(":", 1)[1]
        api = f"http://127.0.0.1:{api_port}"
        ui = f"http://127.0.0.1:{ui_port}"
        wait_for(lambda: get(f"{api}/health")["status"] == "ok", "API readiness")
        wait_for(lambda: get(f"{ui}/_stcore/health"), "Streamlit readiness")
        expected = json.loads((ROOT / "tests/fixtures/expected_activity.json").read_text())
        compose("run", "--rm", "replay", "python", "-m", "replay.replay_producer",
                "--end", str(expected["phase_one_records"]), "--interval", "0")

        def check_activity():
            for wanted in expected["rows"]:
                url = (f"{api}/api/v1/activity?wiki={wanted['wiki']}"
                       "&window=2026-01-01T00%3A00%3A00%2B00%3A00")
                body = get(url)
                if not body["data"]:
                    return False
                row = body["data"][0]
                if any(row[key] != value for key, value in wanted.items()):
                    return False
            return True

        wait_for(check_activity, "fixture activity counts")
        # Gold has its own checkpoint: prove it consumed the first phase before advancing time.
        def gold_consumed_first_phase():
            progress = json.loads(compose("exec", "-T", "spark", "cat", "/data/progress.json"))
            if not all(progress["active_queries"].values()):
                raise RuntimeError("A streaming query is inactive")
            gold = progress["queries"].get("activity_gold") or {}
            watermark = gold.get("eventTime", {}).get("watermark", "1970")
            return watermark > "1970-01-01T00:00:00"

        wait_for(gold_consumed_first_phase, "Gold query consumes fixture phase one")
        compose("run", "--rm", "replay", "python", "-m", "replay.replay_producer",
                "--start", str(expected["phase_one_records"]), "--interval", "0")
        wait_for(check_activity, "stable counts after watermark advance")
        compose("exec", "-T", "dashboard", "python", "scripts/inspect_dashboard.py", timeout=240)
        lake = f"file:///data/wikipulse/{run_id}"
        wait_for(lambda: compose("exec", "-T", "spark", "python", "scripts/inspect_lake.py",
                                 "--base", lake, timeout=90), "Bronze/Silver/Gold correctness", 240)
        for endpoint in ("trends", "suspicious-edits", "events/fixture-001"):
            try:
                get(f"{api}/api/v1/{endpoint}")
                raise AssertionError(f"{endpoint} must be explicitly deferred")
            except urllib.error.HTTPError as exc:
                assert exc.code == 501
        report.update({"status": "passed", "api_url": api, "dashboard_url": ui,
                       "checks": ["API readiness", "UI readiness", "activity counts two wikis",
                                  "dashboard counts/window/readiness",
                                  "dedup/invalid/canary", "Bronze/Silver/Gold", "HTTP501 deferred"]})
        return report
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        try:
            logs = compose("logs", "--no-color", "--tail=200", timeout=30)
            (output_dir / "services.log").write_text(logs, encoding="utf-8")
        finally:
            (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2), flush=True)
            print(f"Evidence: {output_dir}", flush=True)
            if not keep:
                # Only delete this unique test project's data, never the developer project.
                compose("down", "--volumes", "--remove-orphans", timeout=120)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="Keep isolated stack for inspection")
    parser.add_argument("--no-build", action="store_true")
    options = parser.parse_args()
    run_smoke(keep=options.keep, build=not options.no_build)
