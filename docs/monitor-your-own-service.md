# Monitor your own service

Adding a service to Firebreak is adding one file. Prometheus watches
`platform/prometheus/targets/` and picks up new or edited files on its own:
no restart, no change to `prometheus.yml`.

## 1. Describe the service

Create `platform/prometheus/targets/<your-service>.yml`:

```yaml
- targets: ["my-service:8080"]
  labels:
    service: my-service
```

- **`targets`** is `host:port` of an HTTP endpoint that serves Prometheus
  metrics at `/metrics`. From inside Compose, use the container's name. For
  something outside Compose, use an address Prometheus's container can reach,
  such as a LAN IP.
- **`service`** is required. It becomes the series' `job` label, so you query
  `up{job="my-service"}`, and the alert below names the service by it. Without
  it, every target lands in one job called `services` and the alerts can't
  tell them apart.
- Add any other labels you want to filter by (`team`, `env`); they're attached
  to every series from that target.

[`targets/platform.yml`](../platform/prometheus/targets/platform.yml) is a
real example: Firebreak monitoring its own Alertmanager, Grafana, Loki and
Tempo.

## 2. Check it works

Within a few seconds, open <http://localhost:9090/targets> and look for your
service under the `services` pool, **UP**. Or from a terminal:

```bash
curl -s localhost:9090/api/v1/query --data-urlencode 'query=up{job="my-service"}'
```

`value` should be `1`. A `0` means Prometheus reached the address but the
scrape failed; no result at all means the file wasn't picked up (check the
YAML, and that the file ends in `.yml`).

## 3. What you get for free

- **`ServiceDown`**, a ticket-level alert when the service can't be scraped
  for 2 minutes. It goes through Alertmanager to Telegram like the rest.
- Its metrics in Grafana's Explore view, under its own `job`.

Service-level objectives, latency alerts and dashboards are specific to each
service, so those are yours to add: `slos/` and `platform/grafana/dashboards/`
show how `orders-api` does it.
