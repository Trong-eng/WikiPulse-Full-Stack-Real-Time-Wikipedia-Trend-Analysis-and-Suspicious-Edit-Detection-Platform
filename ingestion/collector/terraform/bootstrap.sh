#!/bin/bash
set -euo pipefail

revision="$1"
repo=/opt/wikipulse
dnf -y install docker git python3.11 python3.11-pip
systemctl enable --now docker
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"
curl -fsSL --retry 3 -o docker-compose-linux-x86_64 https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64
curl -fsSL --retry 3 -o docker-compose-linux-x86_64.sha256 https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64.sha256
sha256sum -c docker-compose-linux-x86_64.sha256
install -D -m 0755 docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose
git clone https://github.com/Trong-eng/WikiPulse-Full-Stack-Real-Time-Wikipedia-Trend-Analysis-and-Suspicious-Edit-Detection-Platform.git "$repo"
cd "$repo"
git checkout --detach "$revision"
test "$(git rev-parse HEAD)" = "$revision"
test -z "$(git status --porcelain=v1)"
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]' -r dashboard/requirements.txt
git --version
python3.11 --version
docker version --format '{{.Server.Version}}'
docker compose version
