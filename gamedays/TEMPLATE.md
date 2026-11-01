# GD-0N: <scenario>

**Date:** YYYY-MM-DD · **Incident commander:** · **Scribe:**

## Scenario

What we are going to break, in one sentence.

## Steady-state hypothesis

Something we can check with a number. For example: "the availability alert
reaches Telegram within N minutes, and the availability SLI is back within
target M minutes after mitigation".

## Injection

The exact command.

## Blast radius

What can be affected, and what must not be.

## Abort conditions

When we stop early, no matter what.

## Rollback

The exact command that undoes the injection.

## Expected alert and runbook

Which alert should fire and which runbook it points to.

## Results

| Mark | Time |
| :--- | :--- |
| Injection started | |
| Alert received (detection) | |
| Mitigation applied | |
| Service healthy again (recovery) | |

**MTTD:** · **MTTR:** · **Hypothesis held:** yes / no

## Findings

What surprised us, and what we will change. Link the postmortem if there is one.
