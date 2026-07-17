"""Step 12 SRE baseline: structured request logs + Prometheus metrics."""

import json
import logging
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger("thejourney.access")

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _route_path(request: Request) -> str:
    """Route template (/weights/{weight_id}) instead of the raw URL, so metric
    label cardinality stays bounded."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def observe(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = _route_path(request)
        if path not in ("/metrics", "/healthz"):
            REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(duration)
            logger.info(
                json.dumps(
                    {
                        "event": "request",
                        "method": request.method,
                        "path": path,
                        "status": response.status_code,
                        "duration_ms": round(duration * 1000, 1),
                    }
                )
            )
        return response

    @app.get("/metrics", tags=["health"], include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
