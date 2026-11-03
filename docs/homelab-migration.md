# Homelab migration plan

Firebreak runs on a workstation today. This is the plan for moving it to the
homelab: a Proxmox VE host with VLANs for management (10), DevOps and
Kubernetes (20), AI services (30) and IoT (40), and Proxmox Backup Server for
backups. It's a plan, not the migration.

## Where it runs

**Docker Compose in a dedicated VM on the management VLAN**, not the Helm chart
inside the homelab's Kubernetes cluster.

The monitor has to survive what it monitors. If Firebreak ran inside the
cluster, a broken cluster (control plane down, network plugin failing,
storage full) would take the alerting down with it, at the exact moment it's
needed. A separate VM keeps watching when the cluster doesn't answer, and its
`up == 0` is precisely the alert you want.

| Option | Verdict |
| :--- | :--- |
| Compose in a VM (VLAN 10) | **Chosen.** Independent of the cluster, simple to back up whole with PBS |
| Compose in an LXC container | Lighter, but Docker inside LXC needs nesting and relaxed AppArmor, and breaks on host upgrades |
| Helm chart in the cluster | Good for learning (phase 10), wrong place for the watcher |

The VM needs about 4 GB of RAM and 50 GB of disk to start (see Retention).

## What changes

**Targets.** The homelab's services are added through
`platform/prometheus/targets/`, the same way any service is:

| Target | How | Labels |
| :--- | :--- | :--- |
| Proxmox nodes | `node_exporter` on each node, or `prometheus-pve-exporter` | `service: proxmox` |
| Kubernetes cluster | kube-state-metrics and node metrics from the cluster, scraped from outside | `service: k3s` |
| n8n, Ollama (VLAN 30) | Their metrics endpoints | `service: n8n`, `service: ollama` |
| NAS and PBS | `node_exporter` | `service: nas`, `service: pbs` |

Firewall rules allow only the monitoring VM to reach those ports, from VLAN 10
into the others; nothing goes the other way.

**Automation.** n8n and Ollama already live in their own LXC on VLAN 30, so the
VM doesn't start the `automation` profile. Alertmanager's `n8n` receiver
points at the homelab's n8n instead of the Compose one, and its socket proxy
stays where n8n is.

**Retention.** More history, sized from the workstation's measured rate (about
250 MB for 30 days at 900 series). With a few thousand series in the homelab:
Prometheus 90 days with a 30 GB cap, Loki 30 days, Tempo 7 days. Keep the size
cap under 85% of the disk given to it, because the WAL counts too.

**Backups.** `scripts/backup.sh` runs nightly from cron inside the cheap-power
window (after 20:00), and its folder goes to the NAS. PBS also backs up the
whole VM, so there are two independent ways back: restore the VM, or restore
the volumes into a fresh install (drill-tested at 30 s).

**Access.** The ports stay on `127.0.0.1` inside the VM. Grafana is published
only through the homelab's reverse proxy (Nginx Proxy Manager or Traefik) with
TLS, never by opening ports on the VM.

**The test bed.** `orders-api` stays: it's what game days break to prove the
alerts still work after the move.

## How to cut over

1. Install on the VM from the README (`init-env.sh`, `up`), plus the homelab
   targets.
2. Run **both installations in parallel for a week**: the workstation and the
   VM watch the same targets, with Telegram on both, labelled so you can tell
   the messages apart.
3. Compare: every alert that fires on one must fire on the other. Run GD-01
   and GD-04 against the VM to prove the paging path end to end.
4. Only then stop the workstation's stack.

## How to roll back

The workstation install isn't deleted during the parallel week or for a while
after it. If the VM misbehaves:

1. Start the workstation stack again (`docker compose up -d --wait`); it
   still has its own data.
2. If the VM's data is needed, restore its latest backup on the workstation
   with `scripts/restore.sh`.
3. Point Telegram and the reverse proxy back, fix the VM, and repeat the
   parallel week.
