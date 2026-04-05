from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, species, observations

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
