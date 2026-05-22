from fastapi import FastAPI
from routes import metrics, nodes, alerts
from db import init_db

app = FastAPI(title="Sentinel API", version="1.0.0")

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Include routes (Phase 4.1)
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
# app.include_router(nodes.router, prefix="/api/v1", tags=["nodes"])
# app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
