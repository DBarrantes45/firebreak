# Error budget policy

The SLOs in [`slos/`](../slos/README.md) leave room for things to go wrong:
0.1% of requests may fail and 1% may be slow over any 30 days. That room is
the error budget. This page says what happens when it runs low, so the
decision is made now, calmly, and not in the middle of an incident.

It is not a punishment. Its only job is to decide what to work on next.

## While there is budget left

Ship features as usual. Spending budget on purpose is fine: a risky change,
an experiment, a dependency upgrade. That is what the budget is for.

## When the budget is gone

Until the SLO is back within target, only reliability fixes and security
patches get merged. New features wait.

## When one incident eats a big piece

If a single incident burns more than 20% of the 30-day budget, it gets a
written postmortem with at least one action item that is actually scheduled.

## What does not count

Load tests and announced game days are planned and expected to fail things.
They run against separate routes or with a label that the SLO queries
exclude, so they don't spend budget.

## Alerts

The burn-rate alerts follow the multi-window approach from Google's SRE
Workbook:

| Severity | Fires when the budget would be gone in | Windows |
| :--- | :--- | :--- |
| page | about 2 days (burn rate 14.4) or 5 days (burn rate 6) | 5m + 1h, 30m + 6h |
| ticket | about 10 days (burn rate 3) or 30 days (burn rate 1) | 2h + 1d, 6h + 3d |

A page means someone looks now. A ticket means someone looks this week.
