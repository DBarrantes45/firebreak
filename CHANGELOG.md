# Changelog

All notable changes to this project are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-24

The victim app: a small service to break on purpose.

### Added

- `orders-api` (FastAPI + Postgres): `GET /products` and `POST /orders`.
- Liveness (`/healthz`, never touches the database) and readiness
  (`/readyz`, 503 when Postgres is down) probes.
- Programmable failures at `/admin/chaos`: error rate, latency on a fraction
  of requests and a memory leak. Off unless `FIREBREAK_CHAOS_ENABLED=true`.
- Docker image (`python:3.12.15-slim`, non-root user) and `compose.yaml`
  with Postgres 18, healthchecks and startup ordering.
- Tests with pytest that run without a database.
- Pre-commit hooks: gitleaks, ruff, yamllint, hadolint.
- CI on every pull request: lint, tests, compose validation, image scan with
  trivy and a full-history secret scan.
