# Run it on Kubernetes

The same app on a local [kind](https://kind.sigs.k8s.io/) cluster, with its own
Helm chart and the standard monitoring stack. Kubernetes 1.37, which matches
the current CKA curriculum.

You need kind 0.33, kubectl 1.37 and Helm 3.

## 1. A cluster with its own kubeconfig

```bash
source deploy/k8s/env.sh
kind create cluster --name firebreak --config deploy/k8s/kind-config.yaml
```

`env.sh` points `KUBECONFIG` at `~/.kube/firebreak.yaml` and prints the active
context. Source it in every terminal: without it, kubectl falls back to
`~/.kube/config` and talks to whatever cluster that one points at.

## 2. Postgres

```bash
kubectl create namespace firebreak
kubectl -n firebreak create secret generic orders-db \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 24)"
kubectl apply -f deploy/k8s/postgres.yaml
```

The password goes straight from `openssl` into the cluster and never touches a
file.

## 3. Monitoring

```bash
kubectl create namespace monitoring
kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$(openssl rand -base64 24)"
helm upgrade --install kps \
  oci://ghcr.io/prometheus-community/charts/kube-prometheus-stack \
  --version 92.14.1 -n monitoring -f deploy/k8s/monitoring-values.yaml
```

[`monitoring-values.yaml`](../../deploy/k8s/monitoring-values.yaml) explains
each choice: no default Grafana password, Prometheus picks up every
ServiceMonitor, and the control-plane targets kind can't expose are off so
their alerts don't fire forever.

## 4. The app

```bash
helm upgrade --install orders-api deploy/k8s/charts/orders-api -n firebreak
```

The chart pulls the released image from GHCR, runs two replicas, and brings a
ServiceMonitor plus the same alerting rules Compose uses. Those rules live in
`platform/prometheus/rules/`; `scripts/sync-k8s-rules.sh` copies them into the
chart and CI fails if the copies drift.

## Looking around

The Compose stack may already hold ports 3000 and 9090, so use others:

```bash
kubectl -n monitoring port-forward svc/kps-grafana 3001:80
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9091:9090
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

## Clean up

```bash
kind delete cluster --name firebreak
```

Closing the terminal doesn't stop the cluster; this does.
