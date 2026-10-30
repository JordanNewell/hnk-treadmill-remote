# Security Policy

## Reporting a Vulnerability

Email **security@jordannewell.com** with details and repro steps.

**Acknowledgment SLA: 72 hours** (solo maintainer with day-job + 15-agent fleet — 48h broke credibility when missed).

## Disclosure

- Reporter credited in release notes unless they prefer otherwise.
- Coordinated disclosure after fix ships.
- No bug bounty program (yet).

## Scope

- The BLE controller (`hnk.py`, `hnk_serve.py`) and its HTTP API
- The protocol documentation in `README.md`

## Out of scope

- Vulnerabilities in dependencies (report upstream)
- The treadmill firmware itself (report to the vendor; we can't fix it)
- Physical safety incidents from operating the belt (see Safety in README)
