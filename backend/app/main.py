from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes.ingest import router as ingest_router
from app.routes.readings import router as readings_router
from app.routes.fan import router as fan_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dorm Guardian Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(readings_router)
app.include_router(fan_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "dorm-guardian-mock-api",
    }