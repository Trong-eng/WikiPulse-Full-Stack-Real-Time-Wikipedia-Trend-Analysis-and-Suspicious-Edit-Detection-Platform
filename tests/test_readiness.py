"""Exercise the container probe, including stale and partial startup snapshots."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QUERIES = (
    "bronze_raw", "bronze_invalid", "silver_events", "activity_cassandra", "activity_gold",
    "trends_provisional_parquet", "suspicious_parquet", "events_parquet", "trends_gold",
)


@pytest.mark.parametrize("case,code", [
    ("ready", 0), ("missing", 1), ("malformed", 1), ("empty", 1), ("partial", 1),
    ("inactive", 1), ("stale", 1), ("future", 1), ("no_timezone", 1),
])
def test_spark_probe_accepts_only_fresh_complete_active_pipeline(tmp_path, case, code):
    path = tmp_path / "progress.json"
    now = datetime.now(timezone.utc)
    payload = {"updated_at": now.isoformat(), "active_queries": dict.fromkeys(QUERIES, True)}
    if case == "empty":
        payload["active_queries"] = {}
    elif case == "partial":
        del payload["active_queries"]["trends_gold"]
    elif case == "inactive":
        payload["active_queries"]["silver_events"] = False
    elif case in {"stale", "future"}:
        payload["updated_at"] = (now + timedelta(seconds=120 if case == "future" else -120)).isoformat()
    elif case == "no_timezone":
        payload["updated_at"] = now.replace(tzinfo=None).isoformat()
    if case != "missing":
        path.write_text("{invalid" if case == "malformed" else json.dumps(payload))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_spark_ready.py"), "--path", str(path)],
        capture_output=True, text=True,
        env={**os.environ, "SPARK_ANALYTICS_SINK": "parquet"},
    )
    assert result.returncode == code, result.stderr
