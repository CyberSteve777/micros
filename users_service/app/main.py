import logging

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.responses import JSONResponse

from .endpoints.user_router import user_router
from .database import init_db
from elasticsearch import Elasticsearch
import time

app = FastAPI(
    title="Users Service",
    description="Микросервис для управления пользователями и аутентификацией",
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
APP_INFO.labels(app_name="users-service", version="1.1.0").inc(0)

es = Elasticsearch(hosts=["http://elasticsearch:9200"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "users"}

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    body_bytes = await request.body()
    try:
        # Временно подменяем receive для передачи буфера дальше
        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        response = await call_next(Request(request.scope, receive))
    except Exception:
        logging.exception("Ошибка при обработке запроса")
        response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

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

    # Elasticsearch
    try:
        es.index(
            index="users-service-logs",
            document={
                "timestamp": time.time(),
                "method": request.method,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "body": body_bytes.decode(errors="ignore")
            }
        )
    except Exception as e:
        # Не ломаем сервис, если Elasticsearch недоступен
        logging.error(f"Ошибка отправки лога в Elasticsearch: {e}")

    return response


app.include_router(user_router, prefix="/api")

# 🔥 ВОТ ЭТО РЕШАЕТ 404
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
