# SLOs

`orders-api.yml` is the source of truth. Sloth turns it into the Prometheus
rules in `platform/prometheus/rules/`; never edit those by hand, regenerate:

```bash
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" -w /work \
  ghcr.io/slok/sloth:v0.16.0 generate -i slos/orders-api.yml \
  -o platform/prometheus/rules/slo-orders-api.yml
```

Both SLOs use a 30-day window and only count `/products` and `/orders`.
Probes, `/metrics` and `/admin/chaos` are not user traffic, so they stay out.

## Availability: 99.9%

A request is bad when the service answers 5xx. 4xx responses are the
client's fault and don't spend budget. There is no rate limiting yet; if a
429 shows up later, it will count against us, since throttling users is
something the service decided to do.

99.9% over 30 days is about 43 minutes of full outage, or 0.1% of requests
failing all month long.

## Latency: 99% under 250 ms

A request is bad when it succeeds (2xx) but takes longer than 250 ms. Failed
requests are left out because the availability SLO already counts them;
counting them twice would spend budget twice for the same problem.

The target is looser than availability on purpose: people put up with an
occasionally slow page far more readily than with an error. Today `/products`
answers in about 5 ms at p95, so 250 ms leaves plenty of room and only trips
on real trouble.
