import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import adults, content, student, tutor

Base.metadata.create_all(engine)

app = FastAPI(title="SYNiq API", version="0.1.0")

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


@app.get("/health")
def health():
    return {"ok": True}
