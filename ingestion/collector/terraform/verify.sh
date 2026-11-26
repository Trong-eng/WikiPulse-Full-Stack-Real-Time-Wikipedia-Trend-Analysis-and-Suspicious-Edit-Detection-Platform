#!/bin/bash
set -euo pipefail
state_dir=/var/lib/wikipulse
repo=/opt/wikipulse
status=$(cat "$state_dir/status" 2>/dev/null || printf 'NOT_STARTED')
if [ "$status" != READY ]; then
    printf 'Bootstrap %s; xem /var/log/wikipulse-bootstrap.log\n' "$status" >&2
    exit 1
fi
revision=$(cat "$state_dir/source_revision")
cd "$repo"
if [ "$(git rev-parse HEAD)" != "$revision" ] || [ -n "$(git status --porcelain=v1)" ]; then
    echo 'Checkout không khớp SHA hoặc có thay đổi; không chạy verify.' >&2
    exit 1
fi
docker info >/dev/null
docker compose version >/dev/null
test -x .venv/bin/python
echo 'Chạy REPLAY smoke; report và logs sẽ được in tại Evidence.'
PYTHONUTF8=1 .venv/bin/python scripts/smoke_test.py
