# Changelog

All notable changes to this project are listed here.
Versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-25

Metrics: the app can now be watched.

### Added

- RED metrics in `orders-api` at `/metrics`: `http_requests_total` (counter)
  and `http_request_duration_seconds` (histogram), labelled by route template
  so cardinality stays bounded. Unknown paths share the `unmatched` label.
- Prometheus (v3.15.1) scraping the API every 15 seconds.
- Grafana (13.2.4) provisioned as code: Prometheus data source and a
  "Golden signals" dashboard (traffic, errors, latency p50/p95/p99, memory).
  The admin password is required from `.env`; the default admin/admin is off.
- `scripts/generate-traffic.sh` to feed the dashboards.
- Tests that check injected errors are counted (middleware order).
- CI: `promtool check config`, dashboard JSON validation and a smoke test
  that starts the whole stack and checks Prometheus and Grafana.

### Changed

- `/metrics` is excluded from chaos, so scraping keeps working while the app
  is failing on purpose.

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
