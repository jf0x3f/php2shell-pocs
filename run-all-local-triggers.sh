#!/usr/bin/env bash
set -euo pipefail

LAB_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
"$LAB_DIR/run-oom-trigger.sh"
"$LAB_DIR/run-stale-state-trigger.sh"
docker build --platform=linux/amd64 \
    -f "$LAB_DIR/Dockerfile.stale-state-control" \
    -t php2shell-stale-control:8.5.4 \
    "$LAB_DIR"
IMAGE=php2shell-stale-control:8.5.4 SKIP_BUILD=1 \
    "$LAB_DIR/run-stale-state-trigger.sh"
