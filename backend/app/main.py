import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.rate_limit import RateLimitMiddleware
from app.services.seed import seed_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    if s.environment == "production" and s.jwt_secret == "change-me-in-production":
        raise RuntimeError("JWT_SECRET must be set in production")
    if s.auto_create_tables:
        init_db()
    for attempt in range(3):
        try:
            with SessionLocal() as db:
                seed_all(db)
            break
        except Exception:  # concurrent cold starts may both try to insert seeds
            if attempt == 2:
                raise
            time.sleep(1.5)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=f"{s.app_name} API", version="0.1.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "ai_provider": s.ai_provider}

    app.include_router(api_router, prefix=s.api_prefix)
    return app


app = create_app()
