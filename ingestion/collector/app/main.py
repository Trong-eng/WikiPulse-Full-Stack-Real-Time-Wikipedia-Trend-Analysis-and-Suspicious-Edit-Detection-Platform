"""Collector extension point owned by Thành, implemented in week 2."""

import sys

from wikipulse_core.logging import configure_logging


def main() -> None:
    configure_logging("collector")
    print("LIVE collector chưa triển khai. Owner: Thành; checkpoint W2-THANH-01.", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
