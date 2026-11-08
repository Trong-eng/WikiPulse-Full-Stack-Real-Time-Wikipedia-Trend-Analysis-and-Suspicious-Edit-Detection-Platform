"""Host runner: real Kafka/HDFS/Cassandra, isolated namespace, bounded phase commands."""

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
PHASES = ("initial", "late", "retry_failure", "recovered", "finalized",
          "after_restart", "idle_restart")
PUBLISH = {"initial", "late", "retry_failure", "finalized", "after_restart"}


def run(*, build=True, keep=False):
    run_id = f"w3-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid4().hex[:12]}"
    project = f"wikipulse-{run_id}"
    output = ROOT / "artifacts" / run_id
    output.mkdir(parents=True)
    env = dict(os.environ)
    env.update({
        "COMPOSE_PROJECT_NAME": project, "COMPOSE_PROFILES": "full",
        "COMPOSE_FILE": os.pathsep.join(str(ROOT / f) for f in
                                       ("docker-compose.yml", "docker-compose.hdfs.yml")),
        "COMPOSE_PATH_SEPARATOR": os.pathsep, "COMPOSE_DISABLE_ENV_FILE": "1",
        "RUN_ID": run_id, "PIPELINE_MODE": "REPLAY", "PIPELINE_VERSION": "0.2.0",
        "API_HOST_PORT": "0", "DASHBOARD_HOST_PORT": "0", "KAFKA_HOST_PORT": "0",
        "KAFKA_ADVERTISED_EXTERNAL_PORT": "19092", "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
        "KAFKA_RAW_TOPIC": "wikipedia.recentchange.raw",
        "KAFKA_DLQ_TOPIC": "wikipedia.recentchange.dlq",
        "CASSANDRA_HOST": "cassandra", "CASSANDRA_PORT": "9042",
        "CASSANDRA_KEYSPACE": "wikipulse_w3", "WIKI_ALLOWLIST": "enwiki,viwiki",
        "HDFS_BASE_PATH": "hdfs://namenode:9000/wikipulse",
        "HDFS_CHECKPOINT_PATH": "hdfs://namenode:9000/checkpoints",
        "SPARK_ANALYTICS_SINK": "parquet", "SPARK_SCORING_PATH": "/workspace/config/scoring.yaml",
        "USER_HASH_SALT": "w3-synthetic-fixture", "MAX_OFFSETS_PER_TRIGGER": "1000",
        "WATERMARK_DELAY": "10 minutes", "TRIGGER_INTERVAL": "1 second",
    })
    env.pop("COMPOSE_ENV_FILES", None)
    # No permanent Spark service: each phase is a fresh JVM, same HDFS checkpoints.
    command = ["docker", "compose", "-p", project]

    def compose(*args, timeout=300):
        with (output / "commands.log").open("a+", encoding="utf-8") as log:
            log.write(f"$ docker compose {' '.join(args)}\n")
            log.flush()
            start = log.tell()
            result = subprocess.run(command + list(args), cwd=ROOT, env=env,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            log.seek(start)
            text = log.read()
        if result.returncode:
            raise RuntimeError(f"Compose exit {result.returncode}; see {output}/commands.log")
        return text

    report = {"status": "failed", "run_id": run_id, "project": project, "phases": [],
              "scope": "W3 producer HDFS and activity retry; analytics Cassandra/LIVE deferred"}
    print(f"W3 acceptance: {project}; evidence: {output}", flush=True)
    try:
        compose("config", "--quiet")
        if build:
            compose("build", "spark", "api", "replay", timeout=1200)
        # --wait expects long-running services. Run one-shot initializers explicitly
        # so Compose v5 does not mistake their successful exit(0) for startup failure.
        compose("up", "-d", "--wait", "--wait-timeout", "240", "api", "kafka",
                "namenode", "datanode", timeout=360)
        compose("run", "--rm", "--no-deps", "init-topics")
        compose("run", "--rm", "--no-deps", "init-hdfs")
        first_ids = None
        previous_runs = None
        for phase in PHASES:
            print(f"Phase {phase}", flush=True)
            if phase in {"finalized", "after_restart"}:
                # Containers change, HDFS volumes/state must survive. No driver runs here.
                compose("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "180",
                        "namenode", "datanode", timeout=240)
                compose("run", "--rm", "--no-deps", "init-hdfs")
            if phase in PUBLISH:
                compose("run", "--rm", "--no-deps", "replay", "python", "-m",
                        "replay.replay_producer", "--file",
                        f"processing/spark/tests/fixtures/week_three/{phase}.jsonl", "--interval", "0")
            result = compose("run", "--rm", "--no-deps", "spark", "python", "-m",
                             "processing.spark.acceptance.phase_job", phase, timeout=300)
            (output / f"{phase}.log").write_text(result, encoding="utf-8")
            lines = [line for line in result.splitlines() if line.startswith("W3_PHASE_REPORT=")]
            if len(lines) != 1:
                raise AssertionError(f"Missing phase report: {phase}")
            state = json.loads(lines[0].split("=", 1)[1])
            if state["status"] != "passed":
                raise AssertionError(state)
            ids = state["query_ids"]
            if first_ids is None:
                first_ids = ids
            if ids != first_ids:
                raise AssertionError(f"Checkpoint identity changed in {phase}")
            runs = state["query_run_ids"]
            if previous_runs and any(runs[name] == previous_runs[name] for name in runs):
                raise AssertionError("Must restart each query in a new execution")
            previous_runs = runs
            report["phases"].append(state)
            (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["status"] = "passed"
        print("W3 acceptance passed: 7 phases, 9 checkpoint identities preserved", flush=True)
        return report
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        try:
            logs = compose("logs", "--no-color", "--tail=120", timeout=30)
            (output / "services.log").write_text(logs, encoding="utf-8")
        finally:
            (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            if not keep:
                # Only this generated project's volumes, never the dev/lab environment.
                compose("down", "--volumes", "--remove-orphans", timeout=120)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    run(build=not args.no_build, keep=args.keep)
