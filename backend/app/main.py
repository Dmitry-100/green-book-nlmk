from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, species, observations, validation, notifications
from app.routers import identifier as identifier_router
from app.routers import export as export_router
from app.routers import map as map_router
from app.routers import admin as admin_router
from app.routers import media_serve
from app.routers import gamification

app = FastAPI(title="Green Book NLMK API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(media_serve.router)
app.include_router(gamification.router)

from app.config import settings
if settings.app_env == "development":
    from app.routers import dev_auth
    app.include_router(dev_auth.router)
