#!/usr/bin/env bash
set -euo pipefail

LAB_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
IMAGE="php2shell-oom-trigger:8.4.26"
NETWORK="php2shell-oom-net"
TARGET="php2shell-oom-target"
RUNNER_IMAGE="python:3.13-slim"
SCRIPT="$LAB_DIR/trigger_cve_2026_109618.py"
CREATED_NETWORK=0
CREATED_TARGET=0

cleanup() {
    if [[ "$CREATED_TARGET" == 1 ]]; then
        docker rm -f "$TARGET" >/dev/null 2>&1 || true
    fi
    if [[ "$CREATED_NETWORK" == 1 ]]; then
        docker network rm "$NETWORK" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

if docker container inspect "$TARGET" >/dev/null 2>&1; then
    echo "Refusing to reuse existing container named $TARGET" >&2
    exit 2
fi
if docker network inspect "$NETWORK" >/dev/null 2>&1; then
    echo "Refusing to reuse existing network named $NETWORK" >&2
    exit 2
fi

docker build --platform=linux/amd64 -f "$LAB_DIR/Dockerfile.oom-trigger" -t "$IMAGE" "$LAB_DIR"
if ! docker image inspect "$RUNNER_IMAGE" >/dev/null 2>&1; then
    docker pull --platform=linux/amd64 "$RUNNER_IMAGE"
fi

docker network create --internal "$NETWORK" >/dev/null
CREATED_NETWORK=1
docker run -d \
    --name "$TARGET" \
    --network "$NETWORK" \
    --platform linux/amd64 \
    --pids-limit 64 \
    --memory 256m \
    --cpus 1 \
    "$IMAGE" >/dev/null
CREATED_TARGET=1

docker run --rm \
    --network "$NETWORK" \
    --platform linux/amd64 \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --pids-limit 16 \
    --memory 96m \
    --cpus 0.5 \
    --mount "type=bind,src=$SCRIPT,dst=/tmp/trigger.py,readonly" \
    "$RUNNER_IMAGE" python /tmp/trigger.py http://php2shell-oom-target/

echo "--- Apache/PHP diagnostics ---"
docker logs "$TARGET" 2>&1 | tail -40 || true
