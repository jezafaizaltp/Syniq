import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import IS_SQLITE, Base, engine
from .routers import admin, adults, content, results, student, tutor

PRODUCTION = os.environ.get("SYNIQ_ENV") == "production"

# Local development and tests use SQLite and create tables directly.
# PostgreSQL is managed by migrations: `alembic upgrade head`.
if IS_SQLITE:
    Base.metadata.create_all(engine)

app = FastAPI(
    title="SYNiq API",
    version="0.1.0",
    # No public API explorer on the live server.
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None,
    openapi_url=None if PRODUCTION else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(adults.router)
app.include_router(student.router)
app.include_router(content.router)
app.include_router(tutor.router)
app.include_router(admin.router)
app.include_router(results.router)


@app.get("/health")
def health():
    return {"ok": True}
