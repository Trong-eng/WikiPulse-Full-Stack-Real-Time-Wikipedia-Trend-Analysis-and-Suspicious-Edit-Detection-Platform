"""Exit zero only while the complete W2 pipeline publishes fresh live progress."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def ready(path: Path, sink: str) -> bool:
    expected = {
        "bronze_raw", "bronze_invalid", "silver_events", "activity_cassandra", "activity_gold",
        "trends_gold",
    }
    if sink == "parquet":
        expected.update(("trends_provisional_parquet", "suspicious_parquet", "events_parquet"))
    elif sink == "cassandra":
        expected.update(("trends_cassandra", "suspicious_cassandra", "events_cassandra"))
    else:
        return False
    try:
        progress = json.loads(path.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(progress["updated_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        active = progress["active_queries"]
        return 0 <= age <= 60 and set(active) == expected and all(
            value is True for value in active.values()
        )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("/data/progress.json"))
    args = parser.parse_args()
    raise SystemExit(0 if ready(args.path, os.environ.get("SPARK_ANALYTICS_SINK", "parquet")) else 1)
