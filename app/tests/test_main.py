import os
import subprocess
import sys
from pathlib import Path

import main
import pytest


def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_products_fail_when_error_rate_is_one(client):
    client.post("/admin/chaos", json={"error_rate": 1.0})
    response = client.get("/products")
    assert response.status_code == 500


def test_probes_ignore_chaos(client):
    client.post("/admin/chaos", json={"error_rate": 1.0})
    response = client.get("/healthz")
    assert response.status_code == 200


def test_readiness_fail_leaves_liveness_alone(client):
    # The whole point of the experiment: not ready, but alive, so Kubernetes
    # takes the pod out of the Service without restarting it.
    client.post("/admin/chaos", json={"readiness_fail": True})
    assert client.get("/readyz").status_code == 503
    assert client.get("/healthz").status_code == 200
    client.post("/admin/chaos", json={})


def test_chaos_endpoint_does_not_exist_when_disabled():
    # main.py reads the switch at import time, so this needs a fresh process
    # with it unset. 404, not 403: a scanner shouldn't learn the route exists.
    script = (
        "from fastapi.testclient import TestClient\n"
        "import main\n"
        "client = TestClient(main.app)\n"
        "print(client.get('/admin/chaos').status_code, "
        "client.post('/admin/chaos', json={'error_rate': 1}).status_code)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "FIREBREAK_CHAOS_ENABLED"}
    env["PYTHONPATH"] = str(Path(main.__file__).parent)
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout.split() == ["404", "404"], result.stderr


def test_chaos_endpoint_exists_when_enabled(client):
    assert client.get("/admin/chaos").status_code == 200


def test_chaos_rejects_rate_out_of_range(client):
    response = client.post("/admin/chaos", json={"error_rate": 1.5})
    assert response.status_code == 400


def read_counter(client, route, status):
    """Return the current value of http_requests_total for a route and status."""
    text = client.get("/metrics").text
    prefix = (
        f'http_requests_total{{method="GET",route="{route}",status="{status}",'
        'traffic="user"} '
    )
    for line in text.splitlines():
        if line.startswith(prefix):
            return float(line[len(prefix) :])
    return 0.0


def test_metrics_count_errors_injected_by_chaos(client):
    # Guards the middleware order: the metrics middleware must wrap the chaos
    # middleware, or injected 500s would never be counted.
    before = read_counter(client, "/products", "500")
    client.post("/admin/chaos", json={"error_rate": 1.0})
    client.get("/products")
    after = read_counter(client, "/products", "500")
    assert after == before + 1


def test_metrics_count_unhandled_exceptions(client, monkeypatch):
    # The real failure mode: the database is down, so the endpoint raises.
    # It must still show up as a 500 in the metrics, or the SLO goes blind.
    def database_down():
        raise RuntimeError("database down")

    monkeypatch.setattr(main, "acquire_connection", database_down)
    before = read_counter(client, "/products", "500")
    # TestClient re-raises server errors; a real client would get a 500.
    with pytest.raises(RuntimeError):
        client.get("/products")
    after = read_counter(client, "/products", "500")
    assert after == before + 1


def test_metrics_label_unknown_paths_as_unmatched(client):
    client.get("/this/path/does/not/exist")
    assert read_counter(client, "unmatched", "404") >= 1
