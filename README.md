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
SLOs break ([capacity report](loadtests/CAPACITY-REPORT.md)), and six chaos
game days check that each kind of failure actually pages someone. The
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

## Game day results

Each game day breaks one thing on purpose under steady user traffic and
times how long it takes to notice and recover. MTTD runs from injection to
alert; MTTR from injection to healthy again. Run one with
`scripts/gameday.sh GD-0N`.

| Scenario | Alerted? | MTTD | MTTR | Postmortem |
| :--- | :--- | :--- | :--- | :--- |
| [GD-01: 20% of requests fail](gamedays/GD-01-error-spike.md) | Yes | ~2.5 min | ~2.5 min | — |
| [GD-02: 30% of requests are slow](gamedays/GD-02-slow-requests.md) | Yes, slower than expected | ~8.5 min | ~9 min | — |
| [GD-03: memory leak](gamedays/GD-03-memory-leak.md) | Yes | ~2 min | ~2.5 min | — |
| [GD-04: database down](gamedays/GD-04-database-down.md) | Not at first, yes after the fix | 2 min | 6 min | [Outage went unnoticed](postmortems/2026-10-25-database-outage-went-unnoticed.md) |
| [GD-05: database frozen](gamedays/GD-05-database-frozen.md) | Yes | <1 min | ~1 min | — |
| [GD-06: slow network to the database](gamedays/GD-06-slow-network.md) | Not at first, yes on the rerun | ~2 min* | 2 min | — |

\* Flattering: the first run had already filled the alert window. From a
healthy hour, latency incidents take around 10 minutes to page, as GD-02
shows.

## Documentation

- [Architecture](docs/architecture.md): the moving parts and how data flows between them.
- [Run it locally](docs/how-to/run-locally.md): start, stop, reset.
- [Endpoints and ports](docs/reference/endpoints-and-ports.md): every URL in one table.
- [SLOs](slos/README.md) and the [error budget policy](docs/error-budget-policy.md).
- [Runbooks](runbooks/): what to do when each alert fires.
- [Game days](gamedays/) and [postmortems](postmortems/): the failures and what they taught.

## Built with

[FastAPI](https://fastapi.tiangolo.com/), [PostgreSQL](https://www.postgresql.org/),
[Prometheus](https://prometheus.io/), [Grafana](https://grafana.com/oss/grafana/),
[Loki](https://grafana.com/oss/loki/), [Tempo](https://grafana.com/oss/tempo/),
[OpenTelemetry](https://opentelemetry.io/), [Sloth](https://sloth.dev/) and [k6](https://k6.io/).

## License

[MIT](LICENSE)
