# Firebreak

A self-hosted reliability platform: observability, SLOs as code and
automated incident response — validated by breaking it on purpose.

## Why

Most monitoring setups are never tested. You find out an alert doesn't fire
during the incident it was supposed to catch. Firebreak ships with its own
victim app, `orders-api`, which can be told to fail in specific ways (errors,
latency, memory leaks), so every dashboard, SLO and alert can be proven to work.

## What's in it today

A small FastAPI service backed by Postgres, wired to a full observability
stack: Prometheus for metrics, Loki for logs, Tempo for traces, an
OpenTelemetry Collector in the middle and Grafana on top. A request that goes
wrong can be followed from a spike on a dashboard to its trace and its log
lines, all in one place.

On top of that sit two SLOs, one for availability and one for latency, with
burn-rate alerts generated from a short spec. Alertmanager sends them to
Telegram, each with a link to its runbook, and CI proves an outage actually
raises an alert. Load tests measure how much traffic it takes before the
SLOs break ([capacity report](loadtests/CAPACITY-REPORT.md)). Chaos game days
come next; the
[changelog](CHANGELOG.md) tracks what has landed so far.

## Quick start

You need Docker with Compose v2.

```bash
cp .env.example .env    # set real passwords
docker compose up -d --build --wait
scripts/generate-traffic.sh 5
```

Then open Grafana at <http://localhost:3000> and look for the
**Golden signals** dashboard in the Firebreak folder.

## Documentation

- [Architecture](docs/architecture.md): the moving parts and how data flows between them.
- [Run it locally](docs/how-to/run-locally.md): start, stop, reset.
- [Endpoints and ports](docs/reference/endpoints-and-ports.md): every URL in one table.
- [SLOs](slos/README.md) and the [error budget policy](docs/error-budget-policy.md).
- [Runbooks](runbooks/): what to do when each alert fires.

## Built with

[FastAPI](https://fastapi.tiangolo.com/), [PostgreSQL](https://www.postgresql.org/),
[Prometheus](https://prometheus.io/), [Grafana](https://grafana.com/oss/grafana/),
[Loki](https://grafana.com/oss/loki/), [Tempo](https://grafana.com/oss/tempo/),
[OpenTelemetry](https://opentelemetry.io/), [Sloth](https://sloth.dev/) and [k6](https://k6.io/).

## License

[MIT](LICENSE)
