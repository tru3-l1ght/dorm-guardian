from fastapi import FastAPI

app = FastAPI(title="Dorm Guardian Mock API")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "dorm-guardian-mock-api"
    }