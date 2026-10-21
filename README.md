# PHP request-lifecycle trigger labs

This repository contains two small Docker labs for reproducing request trigger
conditions described in PHP's October 2026 advisories for CVE-2026-109618 and
CVE-2026-109619.

These are trigger reproductions, not RCE exploits. They do not shape a heap,
control a stale pointer, disclose process memory, or execute commands. A crash
or memory-limit error alone does not show that those later steps are possible.
Wiz describes its exploit development this way:

> “Building the exploit required chaining multiple flaws and adapting to each target’s memory layout through repeated testing and debugging.”
>
> — [Wiz Research](https://www.wiz.io/blog/php2shell-php-rce)

## What the labs demonstrate

| Advisory | Lab setup and request | Result observed here |
| --- | --- | --- |
| [CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) | PHP 8.4.26 with Apache `mod_php`, `memory_limit=16M`, and `post_max_size=8M`. The runner sends one multipart part with 80,000 headers (about 6.56 MB on the wire). | PHP reports that it exhausted the memory limit while parsing. Apache answers a follow-up health check. This demonstrates the OOM trigger, not the later cleanup corruption, a memory disclosure, or RCE. |
| [CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | PHP 8.5.4 with Apache prefork limited to one worker and `fatal_error_backtraces=1`. One request raises a fatal error; the next applies `auto_detect_line_endings=1` from `.htaccess`. | The consumer connection closes, Apache logs `zend_mm_heap corrupted`, and the next health check reaches a replacement worker. In the control run, `fatal_error_backtraces=0` and all requests complete on the same worker. This demonstrates a worker abort on this setup, not a controlled use-after-free or RCE. |

Both PHP versions are in the affected ranges listed in the advisories. The
patched releases are PHP 8.2.35, 8.3.36, 8.4.27, and 8.5.12.

## Run it

You need Docker Engine with the Docker Compose plugin and network access the
first time the images are pulled. From this directory, run:

```sh
docker compose up --build
```

Compose builds the lab images, runs both trigger cases and the control, then
prints the request results with the Apache/PHP logs. The containers publish no
host ports. Each target and its runner use a separate internal Docker network.
Press Ctrl+C after the results appear, then remove the containers and networks
with:

```sh
docker compose down
```

The built images remain cached.

### CPU architecture

The Compose file uses the host's native Linux architecture; it does not force
`linux/amd64`. The official PHP images provide both AMD64 and ARM64 variants,
so Apple Silicon users do not need AMD64 emulation for this lab. Both trigger
cases and the control were observed on this machine using native ARM64 images
and, separately, AMD64 images under Docker emulation, with the same results.

That only establishes that these trigger checks ran on both architectures.
Memory layout and allocator behavior can still differ across architectures,
builds, and configurations. This lab does not attempt the heap shaping needed
for an RCE chain.

### Target requirements

The runners are wired to the disposable targets created by this Compose file;
they do not accept an arbitrary container or URL. The first case needs the
PHP 8.4.26 Apache image and the memory settings above. The second needs the PHP
8.5.4 Apache image, `fatal_error_backtraces=1`, one persistent prefork worker,
and the producer and consumer endpoints included in this repository. The lab
also enables PHP error display/logging and sends PHP and Apache diagnostics to
the container logs. FPM, FrankenPHP, CGI, and unrelated Docker containers are
not covered.

## How the checks work

The CVE-2026-109618 runner builds a bounded multipart body with 80,000 part
headers and sends it to the PHP 8.4.26 target. The request is below the target's
`post_max_size`, but parsing its headers exceeds PHP's 16 MB `memory_limit`.
The runner then checks whether Apache still answers. Its own container has
separate memory, CPU, and process limits.

The CVE-2026-109619 runner first calls the fatal-error producer, then the
consumer endpoint whose `.htaccess` applies the per-directory INI setting.
Each endpoint returns its worker PID. Apache is configured with one prefork
worker, so the control should report the same PID for each request. In the
vulnerable run, the follow-up health check should report a new PID after
Apache replaces the worker that aborted. The control changes only
`fatal_error_backtraces` to `0`.

## Limits of this PoC

- Neither case demonstrates remote code execution, arbitrary command
  execution, or a controlled memory primitive.
- The CVE-2026-109618 case reaches OOM during multipart parsing. It does not
  demonstrate the cleanup corruption or upload-progress unserializer path
  described in the exploit research, and it does not disclose process memory.
- The CVE-2026-109619 case records a worker abort after a producer/consumer
  sequence. It does not prove control of the stale pointer or exercise the
  separate OPcache type-confusion path.
- Both cases use Apache `mod_php`; they do not test FPM, FrankenPHP, CGI, or
  other server APIs.
- The `fatal_error_backtraces=0` control is a configuration comparison, not a
  patched PHP build.
- PHP image tags and their underlying system packages may change over time.
  These runs used Docker Engine 29.7.2 and Docker Compose 5.4.0; later image
  rebuilds may use different system package revisions.

For production systems, install a vendor-supported PHP release containing the
fixes. Updating is the only complete mitigation described in the PHP release
notice.

## References

- [PHP security release notice (21 October 2026)](https://www.php.net/archive/2026.php#2026-10-21-5)
- [Wiz Research: PHP2Shell technical write-up](https://www.wiz.io/blog/php2shell-php-rce)
- [GHSA-w8hw-w9fx-j79w / CVE-2026-109618](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)
- [GHSA-6wmf-4rv5-p3rp / CVE-2026-109619](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)
