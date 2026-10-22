#!/bin/sh
set -eu

cd "$(dirname "$0")"
mkdir -p aslr-out

cleanup() {
  docker compose -f compose.yaml down --remove-orphans
}
trap cleanup EXIT INT TERM

if [ ! -f upstream/exploit.py ]; then
  echo "ASLR PoC submodule is missing. From the repository root, run:" >&2
  echo "  git submodule update --init --recursive" >&2
  exit 1
fi

docker compose -f compose.yaml up -d

ready=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 http://127.0.0.1:8089/index.php >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "PHP target did not become ready on 127.0.0.1:8089" >&2
  docker compose -f compose.yaml logs --no-color target >&2
  exit 1
fi

python3 upstream/exploit.py \
  -u http://127.0.0.1:8089/index.php \
  --docker-container php2shell-aslr-target \
  --offsets-file aslr-out/offsets.env \
  --proof-file aslr-out/p1
