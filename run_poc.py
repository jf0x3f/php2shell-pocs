#!/usr/bin/env python3
"""Select and run one trigger case in this repository's isolated Compose lab."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = {
    "oom": {
        "label": "CVE-2026-109618 multipart OOM trigger",
        "target": "oom-target",
        "runner": "oom-runner",
    },
    "stale": {
        "label": "CVE-2026-109619 producer/consumer trigger",
        "target": "stale-target",
        "runner": "stale-runner",
    },
    "control": {
        "label": "CVE-2026-109619 fatal_error_backtraces=0 control",
        "target": "stale-control",
        "runner": "stale-control-runner",
    },
}


def compose(*args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        text=True,
        check=False,
        capture_output=capture_output,
    )


def choose_case(requested: str | None) -> str:
    if requested:
        return requested

    print("Choose a local trigger case:")
    print("  1) CVE-2026-109618 multipart OOM")
    print("  2) CVE-2026-109619 producer/consumer")
    print("  3) CVE-2026-109619 control (fatal_error_backtraces=0)")
    answer = input("Selection [1-3]: ").strip()
    choices = {"1": "oom", "2": "stale", "3": "control"}
    if answer not in choices:
        raise SystemExit("Choose 1, 2, or 3.")
    return choices[answer]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manually run one trigger case against this repository's local Docker lab."
    )
    parser.add_argument("case", nargs="?", choices=CASES, help="oom, stale, or control; omit for a prompt")
    args = parser.parse_args()

    case_name = choose_case(args.case)
    case = CASES[case_name]

    existing = compose("ps", "-a", "-q", capture_output=True)
    if existing.returncode:
        detail = existing.stderr.strip() or existing.stdout.strip()
        print(f"Could not inspect the Compose lab: {detail}", file=sys.stderr)
        return existing.returncode
    if existing.stdout.strip():
        print(
            "This Compose project already has containers. Stop or remove the existing lab "
            "with `docker compose down`, then run this script again.",
            file=sys.stderr,
        )
        return 2

    print(f"\nRunning {case['label']}\n")
    try:
        started = compose("up", "-d", "--build", case["target"])
        if started.returncode:
            return started.returncode

        triggered = compose("run", "--rm", "--no-deps", case["runner"])

        print(f"\n--- {case['target']} PHP/Apache logs ---")
        compose("logs", "--no-color", "--tail=80", case["target"])
        return triggered.returncode
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    finally:
        print("\nRemoving this run's containers and networks...")
        stopped = compose("down", "--remove-orphans")
        if stopped.returncode:
            print("Cleanup failed; run `docker compose down` from the repository directory.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
