# PHP 2026 request-lifecycle PoCs

Two small Docker labs for exercising trigger conditions described in PHP's
October 2026 advisories for CVE-2026-109618 and CVE-2026-109619. The [Wiz
write-up](https://www.wiz.io/blog/php2shell-php-rce) gives useful context on
the exploit chains behind them.

These are trigger reproductions, not working RCE exploits. They do not try to
run a command or shape a heap for code execution. The second test can abort a
PHP/Apache worker, so run the scripts only against the disposable containers
they create.

Triggering the bug is only the first step toward RCE. The published exploit
research chains multiple memory-safety conditions and relies on attacker-shaped
heap reuse to turn a stale pointer or corrupted state into a useful primitive.
Some demonstrated paths also use a separate memory disclosure to resolve
addresses. Allocator behavior, PHP build options and extensions affect the
layout, so a crash alone is not evidence of code execution. This lab stops
before heap grooming, memory disclosure or command execution.

## What the tests show

| Advisory | Local setup and request | Result observed in this lab |
| --- | --- | --- |
| [CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) | PHP 8.4.26 with Apache `mod_php`, `memory_limit=16M`; one multipart part with 80,000 headers (about 6.56 MB). | PHP reports that it exhausted the memory limit while parsing. Apache answered a subsequent health check. This demonstrates the OOM trigger, not the invalid-state cleanup or an RCE. |
| [CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | PHP 8.5.4 with one persistent Apache prefork worker. A request raises a fatal error with `fatal_error_backtraces=1`; the next request applies `auto_detect_line_endings=1` from `.htaccess`. | In the vulnerable run, the producer responded from one worker, the consumer connection closed, and the follow-up health check came from a replacement worker. Apache logged `zend_mm_heap corrupted` and the old child exited with `Abort`. With `fatal_error_backtraces=0`, all three requests stayed on the same worker and completed. This demonstrates a crash on this configuration, not controlled use-after-free or code execution. |

Both PHP versions are in the affected ranges listed in the advisories. The
fixed releases listed there are PHP 8.2.35, 8.3.36, 8.4.27 and 8.5.12.

## Run it

You need Docker Engine with Linux container support, a shell, and network access
the first time the base images are pulled. The scripts request `linux/amd64`;
Docker's amd64 emulation works on Apple Silicon, though it may run more slowly.

To build and run both trigger cases plus the CVE-2026-109619 control with
Docker Compose:

```sh
docker compose up
```

Compose builds the targets, starts the request runners, and prints their output
alongside the PHP logs. No host ports are published; each target and its runner
share a separate internal network. When the results have printed, press
Ctrl+C to stop the containers, then use `docker compose down` to remove the
stopped containers and networks.

From this directory, run both tests and the CVE-2026-109619 control:

```sh
./run-all-local-triggers.sh
```

Or run one at a time:

```sh
./run-oom-trigger.sh
./run-stale-state-trigger.sh
```

The combined run builds the control image with `fatal_error_backtraces=0` and
repeats the stale-state requests against it. Each runner prints the request
results and the relevant Apache/PHP log output.

The tests use internal Docker networks and publish no host ports. The request
generators only accept the lab's fixed container names. On exit, the scripts
remove the containers and networks they created; Docker keeps the built images
cached.

## How the harnesses work

`trigger_cve_2026_109618.py` builds a bounded multipart body with 80,000 part
headers, sends it to the PHP 8.4.26 container, then checks whether Apache still
answers. The target's PHP memory limit is 16 MB. The runner container has its
own memory, CPU and process limits.

`trigger_cve_2026_109619.py` first calls the fatal-error producer, then the
consumer endpoint whose `.htaccess` applies the deprecated per-directory INI
setting. Each endpoint returns its worker PID in a response header. Apache is
configured with one prefork worker; in the control run, the producer, consumer
and health check should report the same PID. In the vulnerable run, the
follow-up health check should report a new PID after Apache replaces the worker
that aborted. The script also reports the target logs. The control image
changes only `fatal_error_backtraces` to `0`.

## Relation to the published exploit research

Wiz describes the exploit development this way:

> “Building the exploit required chaining multiple flaws and adapting to each target’s memory layout through repeated testing and debugging.”
>
> — [Wiz Research](https://www.wiz.io/blog/php2shell-php-rce)

The Wiz article describes more than these trigger checks. For CVE-2026-109618,
it discusses a session upload-progress unserializer use-after-free and a
separate process-memory disclosure. This lab sends a multipart request that
exhausts PHP's memory limit; it does not demonstrate the unserializer use-after-free
or disclose process memory.

For CVE-2026-109619, the article describes a fatal-error backtrace use-after-free
and an OPcache type-confusion path. This lab follows the fatal-error plus early
INI-diagnostic sequence and records the worker replacement after the abort. It
does not control the stale pointer, exercise the OPcache path, or build an RCE
chain. Those distinctions matter: a reproducible crash is useful evidence of
the trigger, but it is not an exploit primitive.

## What this does not establish

- Neither test demonstrates remote code execution, a controlled memory
  primitive, or arbitrary command execution.
- The CVE-2026-109618 test reaches an OOM during multipart parsing. It does not
  demonstrate the later cleanup corruption described in the advisory.
- The CVE-2026-109619 result is specific to the tested PHP image, Apache
  configuration and request sequence. A worker abort is evidence of a memory
  safety failure, but it is not proof that the stale pointer was controlled.
- These are `mod_php` tests, not coverage of FPM, FrankenPHP, CGI, or other
  server APIs.
- The control is a configuration check, not a run against a patched PHP build.
  The tagged images and observed behavior can change over time.

For production systems, use a vendor-supported PHP build containing the fixes.
The PHP release notice says updating is the only complete mitigation.

## References

- [PHP security release notice (21 October 2026)](https://www.php.net/archive/2026.php#2026-10-21-5)
- [Wiz Research: PHP2Shell technical write-up](https://www.wiz.io/blog/php2shell-php-rce)
- [GHSA-w8hw-w9fx-j79w / CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)
- [GHSA-6wmf-4rv5-p3rp / CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)
