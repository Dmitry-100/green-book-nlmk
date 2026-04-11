from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.observability import configure_logging, init_sentry
from app.routers import health, species, observations, validation, notifications
from app.routers import identifier as identifier_router
from app.routers import export as export_router
from app.routers import map as map_router
from app.routers import admin as admin_router
from app.routers import dashboard as dashboard_router
from app.routers import media_serve
from app.routers import gamification
from app.routers import metrics as metrics_router

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_production_config()
    init_sentry()
    yield


app = FastAPI(
    title="Green Book NLMK API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
if settings.api_gzip_enabled and settings.api_gzip_minimum_size > 0:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.api_gzip_minimum_size,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.api_rate_limit_enabled and settings.api_rate_limit_per_minute > 0:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.api_rate_limit_per_minute,
    )
app.include_router(health.router)
app.include_router(species.router)
app.include_router(observations.router)
app.include_router(validation.router)
app.include_router(notifications.router)
app.include_router(identifier_router.router)
app.include_router(export_router.router)
app.include_router(map_router.router)
app.include_router(admin_router.router)
app.include_router(dashboard_router.router)
app.include_router(media_serve.router)
app.include_router(gamification.router)
app.include_router(metrics_router.router)

if settings.app_env == "development" and settings.enable_dev_auth:
    from app.routers import dev_auth

    app.include_router(dev_auth.router)
