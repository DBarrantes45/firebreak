import asyncio
import json
import logging
import os
import random
import sys
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from psycopg_pool import ConnectionPool, PoolTimeout
from pydantic import BaseModel
from starlette.routing import Match

tracer = trace.get_tracer("orders-api")

# ---------------------------------------------------------------------------
# Logging: JSON lines on stdout with the trace_id of the current request.
# opentelemetry-instrument also ships every record to Loki over OTLP.

# Only these extra fields reach the logs, so personal data can't leak by accident.
LOG_EXTRA_FIELDS = [
    "order_id",
    "product_id",
    "quantity",
    "path",
    "error_rate",
    "latency_ms",
    "latency_rate",
    "leak_mb_per_request",
]


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_line = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }

        for field in LOG_EXTRA_FIELDS:
            if hasattr(record, field):
                log_line[field] = getattr(record, field)

        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            # The SDK stores the ids as integers; Tempo expects hex text.
            log_line["trace_id"] = trace.format_trace_id(span_context.trace_id)
            log_line["span_id"] = trace.format_span_id(span_context.span_id)

        return json.dumps(log_line)


logger = logging.getLogger("orders-api")
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(JsonFormatter())
logger.addHandler(stdout_handler)

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

# Opening a connection costs ~4 ms (measured in a trace); the query ~0.1 ms.
# The pool keeps connections open and lends them out. Created at startup.
pool = None


def create_pool():
    conninfo = psycopg.conninfo.make_conninfo(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=2,
    )
    return ConnectionPool(
        conninfo,
        min_size=2,
        max_size=10,
        # Each statement commits on its own: no transaction left open.
        kwargs={"autocommit": True},
        # Test a connection before lending it, so a database restart
        # doesn't hand out dead connections.
        check=ConnectionPool.check_connection,
        open=False,
    )


def acquire_connection():
    # Wait at most 2 s for a free connection: a probe or a request must
    # never hang on a dead database.
    with tracer.start_as_current_span("db.pool.acquire"):
        return pool.getconn(timeout=2)


def release_connection(connection):
    pool.putconn(connection)


# ---------------------------------------------------------------------------
# App


@asynccontextmanager
async def lifespan(app):
    global pool
    pool = create_pool()
    pool.open(wait=True, timeout=10)

    connection = acquire_connection()
    try:
        connection.execute(CREATE_TABLES_SQL)
    finally:
        release_connection(connection)

    yield

    pool.close()


app = FastAPI(title="orders-api", lifespan=lifespan)


class NewOrder(BaseModel):
    product_id: int
    quantity: int


# ---------------------------------------------------------------------------
# Endpoints


@app.get("/healthz")
def healthz():
    # Liveness never touches the database: a database outage must not get
    # every replica restarted.
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response):
    try:
        connection = acquire_connection()
        try:
            connection.execute("SELECT 1")
        finally:
            release_connection(connection)
    except (PoolTimeout, psycopg.OperationalError):
        logger.error("database not reachable, instance not ready")
        response.status_code = 503
        return {"status": "unavailable"}

    return {"status": "ready"}


@app.get("/products")
def list_products():
    connection = acquire_connection()
    try:
        rows = connection.execute(
            "SELECT id, name, price FROM products ORDER BY id"
        ).fetchall()
    finally:
        release_connection(connection)

    products = []
    for row in rows:
        products.append({"id": row[0], "name": row[1], "price": float(row[2])})
    return products


@app.post("/orders", status_code=201)
def create_order(order: NewOrder):
    if order.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be greater than 0")

    connection = acquire_connection()
    try:
        product = connection.execute(
            "SELECT id FROM products WHERE id = %s",
            (order.product_id,),
        ).fetchone()

        if product is None:
            logger.warning(
                "order rejected: product not found",
                extra={"product_id": order.product_id},
            )
            raise HTTPException(status_code=404, detail="product not found")

        new_row = connection.execute(
            "INSERT INTO orders (product_id, quantity) VALUES (%s, %s) RETURNING id",
            (order.product_id, order.quantity),
        ).fetchone()
    finally:
        release_connection(connection)

    new_order_id = new_row[0]
    logger.info(
        "order created",
        extra={
            "order_id": new_order_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
        },
    )
    return {
        "id": new_order_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
    }


# ---------------------------------------------------------------------------
# Chaos: programmable failures to prove that dashboards, SLOs and alerts work.
# Lab only: an unauthenticated /admin/chaos would be a security hole in production.

# Off unless FIREBREAK_CHAOS_ENABLED is exactly "true"; then /admin/chaos exists.
CHAOS_ENABLED = os.getenv("FIREBREAK_CHAOS_ENABLED", "false").lower() == "true"

chaos_settings = {
    "error_rate": 0.0,  # fraction of requests that answer 500
    "latency_ms": 0,  # extra delay for slow requests
    "latency_rate": 0.0,  # fraction of requests that are slow
    "leak_mb_per_request": 0,  # memory kept forever on every request
}

leaked_memory = []

PATHS_WITHOUT_CHAOS = ["/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"]


class ChaosSettings(BaseModel):
    error_rate: float = 0.0
    latency_ms: int = 0
    latency_rate: float = 0.0
    leak_mb_per_request: int = 0


@app.middleware("http")
async def chaos_middleware(request: Request, call_next):
    path = request.url.path

    chaos_applies = CHAOS_ENABLED
    if path in PATHS_WITHOUT_CHAOS or path.startswith("/admin"):
        chaos_applies = False

    if chaos_applies:
        if random.random() < chaos_settings["latency_rate"]:
            await asyncio.sleep(chaos_settings["latency_ms"] / 1000)

        if random.random() < chaos_settings["error_rate"]:
            logger.error("chaos: injected error", extra={"path": path})
            return JSONResponse(
                status_code=500, content={"detail": "chaos: injected error"}
            )

        megabytes = chaos_settings["leak_mb_per_request"]
        if megabytes > 0:
            leaked_memory.append(bytearray(megabytes * 1024 * 1024))

    return await call_next(request)


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
        logger.warning("chaos settings changed", extra=dict(chaos_settings))
        return chaos_settings


# ---------------------------------------------------------------------------
# Metrics (RED method). Saturation comes from the process_* metrics that
# prometheus-client exports by itself.

# traffic="loadtest" marks requests sent by k6 (header X-Load-Test), so the
# SLOs can leave planned load tests out, as the error budget policy says.
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests, by method, route, status code and traffic type.",
    ["method", "route", "status", "traffic"],
)

# status_class (2xx/5xx) instead of the exact code keeps cardinality low.
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds, by method, route, status class and traffic type.",
    ["method", "route", "status_class", "traffic"],
)


def find_route_template(request: Request):
    # Route templates, never raw paths: one series per id would exhaust
    # Prometheus memory. Unknown paths share a single label value.
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return "unmatched"


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Defined after chaos_middleware on purpose: the last middleware added is the
# outermost, so this one also measures the failures that chaos injects.
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = str(response.status_code)
    except Exception:
        # An unhandled exception (e.g. the database is down) reaches the
        # client as a 500, but call_next raises instead of returning it.
        # Without this, real failures would never be counted and the SLO
        # alerts would stay silent.
        status = "500"
        raise
    finally:
        duration_seconds = time.perf_counter() - start
        method = request.method
        route = find_route_template(request)
        status_class = status[0] + "xx"
        traffic = "loadtest" if request.headers.get("x-load-test") else "user"

        REQUESTS.labels(
            method=method, route=route, status=status, traffic=traffic
        ).inc()
        REQUEST_DURATION.labels(
            method=method, route=route, status_class=status_class, traffic=traffic
        ).observe(duration_seconds)

    return response
