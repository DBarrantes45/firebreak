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


def test_chaos_rejects_rate_out_of_range(client):
    response = client.post("/admin/chaos", json={"error_rate": 1.5})
    assert response.status_code == 400
