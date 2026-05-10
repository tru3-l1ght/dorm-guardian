from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import ingest, readings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dorm Guardian Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(readings.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "dorm-guardian-mock-api",
    }