import asyncio
import os
import random
import time
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.routing import Match

# ---------------------------------------------------------------------------
# Database

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id         SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id),
    quantity   INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO products (name, price) VALUES
    ('keyboard', 49.90),
    ('mouse', 19.90),
    ('monitor', 189.00)
ON CONFLICT (name) DO NOTHING;
"""


def open_connection():
    """Open a new connection to Postgres using the environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    database = os.environ["POSTGRES_DB"]
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]

    connection = psycopg.connect(
        host=host,
        dbname=database,
        user=user,
        password=password,
        # Give up after 2 seconds instead of waiting forever.
        # A health probe or a request must never hang on a dead database.
        connect_timeout=2,
    )
    return connection


def create_tables():
    """Run CREATE_TABLES_SQL once, when the app starts."""
    connection = open_connection()
    try:
        connection.execute(CREATE_TABLES_SQL)
        connection.commit()
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# App


@asynccontextmanager
async def lifespan(app):
    # Code before "yield" runs once when the app starts.
    # Compose only starts the API after the database healthcheck passes,
    # so the database is ready at this point.
    create_tables()
    yield
    # Code after "yield" would run when the app stops (nothing to do).


app = FastAPI(title="orders-api", lifespan=lifespan)


class NewOrder(BaseModel):
    """The JSON body expected by POST /orders."""

    product_id: int
    quantity: int


# ---------------------------------------------------------------------------
# Endpoints


@app.get("/healthz")
def healthz():
    # Liveness: "is the process alive?"
    # It must NOT touch the database. If it did, a short database outage
    # would make Kubernetes restart every replica at the same time.
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response):
    # Readiness: "can this instance serve traffic right now?"
    # It answers 200 if the database responds and 503 if it does not.
    try:
        connection = open_connection()
        connection.execute("SELECT 1")
        connection.close()
    except psycopg.OperationalError:
        response.status_code = 503
        return {"status": "unavailable"}

    return {"status": "ready"}


@app.get("/products")
def list_products():
    connection = open_connection()
    try:
        rows = connection.execute(
            "SELECT id, name, price FROM products ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    # Each row is a tuple like (1, 'keyboard', Decimal('49.90')).
    # Turn every row into a dictionary so FastAPI returns readable JSON.
    products = []
    for row in rows:
        product = {
            "id": row[0],
            "name": row[1],
            "price": float(row[2]),
        }
        products.append(product)

    return products


@app.post("/orders", status_code=201)
def create_order(order: NewOrder):
    if order.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be greater than 0")

    connection = open_connection()
    try:
        # 1. Check that the product exists.
        product = connection.execute(
            "SELECT id FROM products WHERE id = %s",
            (order.product_id,),
        ).fetchone()

        if product is None:
            raise HTTPException(status_code=404, detail="product not found")

        # 2. Save the order and get back its new id.
        new_row = connection.execute(
            "INSERT INTO orders (product_id, quantity) VALUES (%s, %s) RETURNING id",
            (order.product_id, order.quantity),
        ).fetchone()
        connection.commit()
    finally:
        connection.close()

    new_order_id = new_row[0]
    return {
        "id": new_order_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
    }


# ---------------------------------------------------------------------------
# Chaos: programmable failures

# Master switch. If FIREBREAK_CHAOS_ENABLED is not exactly "true",
CHAOS_ENABLED = os.getenv("FIREBREAK_CHAOS_ENABLED", "false").lower() == "true"

# Current chaos settings. All zeros means "no chaos".
chaos_settings = {
    "error_rate": 0.0,  # 0.2  -> 20% of requests answer 500
    "latency_ms": 0,  # 300  -> slow requests wait 300 ms
    "latency_rate": 0.0,  # 0.1  -> 10% of requests are slow
    "leak_mb_per_request": 0,  # 1    -> each request keeps 1 MB forever
}

# Memory that is never freed (the leak lives here).
leaked_memory = []

# Paths that chaos must never touch: the probes, the chaos endpoints
# themselves and the interactive docs.
PATHS_WITHOUT_CHAOS = ["/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"]


class ChaosSettings(BaseModel):
    """The JSON body expected by POST /admin/chaos."""

    error_rate: float = 0.0
    latency_ms: int = 0
    latency_rate: float = 0.0
    leak_mb_per_request: int = 0


@app.middleware("http")
async def chaos_middleware(request: Request, call_next):
    # A middleware wraps every request: this code runs before the endpoint.
    path = request.url.path

    chaos_applies = CHAOS_ENABLED
    if path in PATHS_WITHOUT_CHAOS:
        chaos_applies = False
    if path.startswith("/admin"):
        chaos_applies = False

    if chaos_applies:
        # 1. Latency: only a fraction of the requests (latency_rate) is slow.
        if random.random() < chaos_settings["latency_rate"]:
            seconds = chaos_settings["latency_ms"] / 1000
            await asyncio.sleep(seconds)

        # 2. Errors: a fraction of the requests (error_rate) answers 500.
        if random.random() < chaos_settings["error_rate"]:
            return JSONResponse(
                status_code=500, content={"detail": "chaos: injected error"}
            )

        # 3. Memory leak: keep N megabytes in a list that is never cleaned.
        megabytes = chaos_settings["leak_mb_per_request"]
        if megabytes > 0:
            leaked_memory.append(bytearray(megabytes * 1024 * 1024))

    # Let the request continue to the real endpoint.
    response = await call_next(request)
    return response


if CHAOS_ENABLED:

    @app.get("/admin/chaos")
    def get_chaos():
        return chaos_settings

    @app.post("/admin/chaos")
    def set_chaos(new_settings: ChaosSettings):
        if new_settings.error_rate < 0 or new_settings.error_rate > 1:
            raise HTTPException(
                status_code=400, detail="error_rate must be between 0 and 1"
            )
        if new_settings.latency_rate < 0 or new_settings.latency_rate > 1:
            raise HTTPException(
                status_code=400, detail="latency_rate must be between 0 and 1"
            )
        if new_settings.latency_ms < 0:
            raise HTTPException(status_code=400, detail="latency_ms must be 0 or more")
        if new_settings.leak_mb_per_request < 0:
            raise HTTPException(
                status_code=400, detail="leak_mb_per_request must be 0 or more"
            )

        chaos_settings["error_rate"] = new_settings.error_rate
        chaos_settings["latency_ms"] = new_settings.latency_ms
        chaos_settings["latency_rate"] = new_settings.latency_rate
        chaos_settings["leak_mb_per_request"] = new_settings.leak_mb_per_request
        return chaos_settings


# ---------------------------------------------------------------------------
# Metrics (Prometheus)
#
# The RED method: for every request we record
#   Rate     -> how many requests arrive  (http_requests_total)
#   Errors   -> how many of them fail     (http_requests_total with status 5xx)
#   Duration -> how long each one takes   (http_request_duration_seconds)
# Saturation (the 4th golden signal) comes for free: prometheus-client
# exports process_resident_memory_bytes and other process_* metrics on Linux.

# Counter: a number that only goes up. Always queried with rate() or increase().
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests, by method, route and status code.",
    ["method", "route", "status"],
)

# Histogram: sorts every duration into buckets (<= 5 ms, <= 10 ms, ... <= 10 s)
# so Prometheus can calculate percentiles like p95 later.
# status_class (2xx/4xx/5xx) instead of the exact code keeps the number of
# time series small while still separating fast errors from real successes.
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds, by method, route and status class.",
    ["method", "route", "status_class"],
)


def find_route_template(request: Request):
    """Return the route template ("/orders"), never the raw path.

    Labels must have a small, fixed set of values. A raw path such as
    "/orders/1834" would create one time series per id and eventually
    run Prometheus out of memory (high cardinality).
    """
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    # Any path the app does not know (typos, scanners) shares one label value.
    return "unmatched"


@app.get("/metrics")
def metrics():
    # Prometheus calls this endpoint every few seconds and stores the numbers.
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ORDER MATTERS. FastAPI runs the LAST middleware added as the OUTERMOST one.
# This middleware is defined after chaos_middleware on purpose: it wraps the
# chaos middleware, so it also sees the 500s and the latency that chaos
# injects. If it were inside, injected failures would never be measured and
# the dashboard would say everything is fine while the app is failing.
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path

    # Do not measure the metrics endpoint itself (it would only add noise).
    if path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - start

    method = request.method
    route = find_route_template(request)
    status = str(response.status_code)  # "200", "404", "500"...
    status_class = status[0] + "xx"  # "2xx", "4xx", "5xx"

    REQUESTS.labels(method=method, route=route, status=status).inc()
    REQUEST_DURATION.labels(
        method=method, route=route, status_class=status_class
    ).observe(duration_seconds)

    return response
