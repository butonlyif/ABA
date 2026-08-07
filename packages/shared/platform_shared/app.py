"""共享 FastAPI 应用工厂。

每个产品后端调用 create_app(product_name, routers) 来创建自己的 FastAPI 实例，
自动获得 CORS / 请求追踪 / health / ready / metrics / 认证路由。
"""

import time
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import SystemEvent
from .routers.auth import router as auth_router
from .routers.expert import router as expert_router


def create_app(
    product_name: str,
    extra_routers: list | None = None,
    lifespan_extra=None,
) -> FastAPI:
    """创建一个带有共享中间件 + 认证路由的 FastAPI 应用。

    Args:
        product_name: 产品名称，用于 app.title
        extra_routers: 产品特定的 APIRouter 列表
        lifespan_extra: 可选的异步 lifespan 上下文管理器
    """
    settings = get_settings()
    request_counts: Counter = Counter()
    request_duration_ms: Counter = Counter()
    request_duration_samples: defaultdict = defaultdict(lambda: deque(maxlen=2048))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.validate_runtime()
        if settings.environment == "development":
            Base.metadata.create_all(engine)
        if lifespan_extra:
            async with lifespan_extra(_):
                yield
        else:
            yield

    app = FastAPI(
        title=product_name,
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            event_db = SessionLocal()
            try:
                event_db.add(SystemEvent(
                    level="error", category="api", message=type(exc).__name__,
                    details={"path": request.url.path, "method": request.method, "request_id": request_id},
                ))
                event_db.commit()
            finally:
                event_db.close()
            raise
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        duration_ms = (time.perf_counter() - started) * 1000
        request_counts[(request.method, path, response.status_code)] += 1
        request_duration_ms[(request.method, path)] += duration_ms
        request_duration_samples[(request.method, path)].append(duration_ms)
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/api/v1/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    # ---- 共享端点 ----
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        from sqlalchemy import select
        db = SessionLocal()
        try:
            db.execute(select(1))
        finally:
            db.close()
        checks = {"database": "ok", "redis": "disabled"}
        if settings.redis_url:
            from redis import Redis
            Redis.from_url(settings.redis_url).ping()
            checks["redis"] = "ok"
        return {"status": "ready", "checks": checks}

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        prefix = product_name.lower().split()[0]
        lines = [
            f"# HELP {prefix}_http_requests_total Total HTTP requests.",
            f"# TYPE {prefix}_http_requests_total counter",
        ]
        for (method, path, status), value in sorted(request_counts.items()):
            lines.append(f'{prefix}_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}')
        lines += [
            f"# HELP {prefix}_http_request_duration_milliseconds_total Cumulative HTTP request duration.",
            f"# TYPE {prefix}_http_request_duration_milliseconds_total counter",
        ]
        for (method, path), value in sorted(request_duration_ms.items()):
            lines.append(f'{prefix}_http_request_duration_milliseconds_total{{method="{method}",path="{path}"}} {value}')
        lines += [
            f"# HELP {prefix}_http_request_duration_milliseconds Recent request duration quantiles.",
            f"# TYPE {prefix}_http_request_duration_milliseconds gauge",
        ]
        for (method, path), samples in sorted(request_duration_samples.items()):
            ordered = sorted(samples)
            if not ordered:
                continue
            for quantile in (0.5, 0.95, 0.99):
                index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
                lines.append(
                    f'{prefix}_http_request_duration_milliseconds{{method="{method}",path="{path}",'
                    f'quantile="{quantile}"}} {ordered[index]:.3f}'
                )
            lines.append(
                f'{prefix}_http_request_duration_milliseconds_count{{method="{method}",path="{path}"}} {len(ordered)}'
            )
        return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")

    # ---- 共享路由：认证 + 专家系统 ----
    app.include_router(auth_router)
    app.include_router(expert_router)

    # ---- 产品特定路由 ----
    if extra_routers:
        for r in extra_routers:
            app.include_router(r)

    return app
