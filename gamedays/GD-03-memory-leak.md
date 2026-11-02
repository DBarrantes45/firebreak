# GD-03: a memory leak runs out the container

**Date:** 2026-10-25 · **Incident commander:** `scripts/gameday.sh --silence` · **Scribe:** rebuilt from Prometheus and Loki

## Scenario

Every request keeps 5 MB forever until the API hits its 512 MB limit.

## Steady-state hypothesis

Memory climbs on the Saturation panel, the kernel kills the container when
it reaches 512 MB, and `OrdersApiDown` reaches Telegram within 2 minutes of
the kill.

## Injection

```bash
scripts/gameday.sh GD-03
```

Under the hood:

```bash
curl -s -X POST localhost:8000/admin/chaos -H 'content-type: application/json' -d '{"leak_mb_per_request": 5}'
```

## Blast radius

`orders-api` and its database only. The observability stack must keep
working, or we can't see what happens.

## Abort conditions

Any other container gets killed.

## Rollback

```bash
docker compose up -d --wait api   # starts a fresh process: the leak is gone
```

## Expected alert and runbook

`OrdersApiDown` (page) → [orders-api-down.md](../runbooks/orders-api-down.md)

## Results

> The run's own output was lost (it lived in `/tmp` and the machine
> rebooted). These marks come from the `ALERTS` series in Prometheus and the
> API logs in Loki, so they're accurate to about 15 seconds. The alert was
> silenced: "received" means it reached Alertmanager, not Telegram.

| Mark | Time |
| :--- | :--- |
| Injection started | 19:35:34 |
| Alert received (detection) | ~19:37:25 |
| Mitigation applied | 19:37:30 |
| Service healthy again (recovery) | ~19:38:05 |

**MTTD:** ~110 s · **MTTR:** ~150 s · **Hypothesis held:** partly, see below

## Findings

- The container died about 11 seconds after the injection. Resident
  memory went from 177 MB to 536 MB between two scrapes (19:35:31 and
  19:35:45), so the Saturation panel showed a cliff, not a climb. At 10 rps
  and 5 MB per request the leak is too fast to watch; a slower leak (say
  0.1 MB per request) would make the panel worth looking at.
- `OrdersApiDown` went pending at 19:36:30 and fired about a minute later,
  roughly 100 seconds after the kill. That part of the hypothesis held.
- The API stayed down until the rollback started it again: the `api` service
  has no restart policy. Adding `restart: unless-stopped` is the obvious
  fix, but then an OOM loop would hide from `OrdersApiDown` and only show
  up as errors. Open question, not changed yet.

## Rerun with automation (phase 8)

**Date:** 2026-11-01 · run with `HANDS_OFF=1 scripts/gameday.sh GD-03`: no
human rollback, the n8n remediation workflow is live (dry run off).

| Mark | Time |
| :--- | :--- |
| Injection started | 17:59:40 |
| Alert received (detection) | 18:01:27 |
| Mitigation applied (bot restarts the API via docker-proxy, HTTP 204) | 18:01:34 |
| Service healthy again (recovery) | 18:01:35 |

**MTTD:** 107 s · **MTTR:** 115 s

- The bot reacted 7 seconds after the alert. Almost all of the MTTR is
  detection: `OrdersApiDown` waits a full minute (`for: 1m`) on purpose.
- The phase 7 run looks similar (~150 s), but there the "human" was the
  script acting the instant the alert fired. A real person needs minutes to
  see the phone and get to a laptop, more at night.
- Restarting really fixes it here because the chaos settings live in the
  API's memory. A real leak would come back, which is why the bot counts.

### What a second crash taught

A follow-up run crashed the API again 3 minutes after the bot's restart,
and nothing restarted it:

- Alertmanager held the new notification for `group_interval` (5 minutes),
  because it belonged to the same alert group.
- Even on time, the bot would have answered "cooling down" and skipped. With
  pages repeating only every hour, that skip meant an hour of downtime.

The bot treated "it crashed again right after my restart" as a repeated
notification. They are different things. The workflow now tells them apart
by the alert's `startsAt`: the same incident is skipped, but a new incident
inside the 5-minute cooldown is a crash loop and escalates to a human. Proven
in dry run: first incident → would restart, repeat → skipped, new incident
right away → escalated.

### Docker's restart policy instead

`restart: unless-stopped` was tried through a temporary override. In one run
Docker restarted the API in under 10 seconds, and `OrdersApiDown` never got
the chance to fire: faster, but nobody hears about it. In the other run the
OOM-killed container stayed down with zero restarts, and a minimal OOM test
outside Compose restarted fine. That run is unexplained, so the policy is
not adopted: the bot restarts and leaves a record, and a crash loop reaches
a human either way.

