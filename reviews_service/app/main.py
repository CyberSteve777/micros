from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app
from .endpoints.review_router import review_router
from .database import init_db
import time

app = FastAPI(
    title="Reviews Service",
    description="Микросервис для управления отзывами о фильмах",
    version="1.1.0"
)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

APP_INFO = Counter(
    "app_info",
    "Application information",
    ["app_name", "version"]
)
APP_INFO.labels(app_name="reviews-service", version="1.1.0").inc(0)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "reviews"}

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    route = request.scope.get("route")
    endpoint = route.path if route else request.url.path

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(time.time() - start_time)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=str(response.status_code)
    ).inc()

    return response

app.include_router(review_router, prefix="/api")

# 🔥 ФИКС
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
