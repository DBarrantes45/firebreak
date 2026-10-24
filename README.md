# Firebreak

A self-hosted reliability platform: observability, SLOs as code and
automated incident response — validated by breaking it on purpose.

## Why

Most monitoring setups are never tested. You find out an alert doesn't fire
during the incident it was supposed to catch. Firebreak ships with its own
victim app, `orders-api`, which can be told to fail in specific ways (errors,
latency, memory leaks), so every dashboard, SLO and alert can be proven to work.

## License

[MIT](LICENSE)
