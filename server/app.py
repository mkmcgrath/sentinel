"""
Sentinel Server - Central monitoring server
FastAPI application for receiving and serving metrics
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from db import init_db, engine
from routes import metrics, nodes, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("Starting Sentinel Server...")
    print(f"Database URL: {os.environ.get('DATABASE_URL', 'Not set')}")

    # Initialize database
    init_db()
    print("Database initialized")

    yield

    # Shutdown
    print("Shutting down Sentinel Server...")
    engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Sentinel Monitoring Server",
    description="Central server for collecting and serving system metrics from distributed nodes",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(metrics.router)
app.include_router(nodes.router)
app.include_router(alerts.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Sentinel Monitoring Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """
    Health check endpoint

    Returns server status and basic statistics
    """
    from sqlalchemy import func
    from db import SessionLocal, Node, Metric

    db = SessionLocal()
    try:
        # Get counts
        node_count = db.query(func.count(Node.id)).scalar()
        metric_count = db.query(func.count(Metric.id)).scalar()
        online_nodes = db.query(func.count(Node.id)).filter(Node.status == "online").scalar()

        return {
            "status": "healthy",
            "database": "connected",
            "statistics": {
                "total_nodes": node_count,
                "online_nodes": online_nodes,
                "total_metrics": metric_count
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )
    finally:
        db.close()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    reload = os.environ.get("RELOAD", "false").lower() == "true"

    print(f"Starting server on {host}:{port}")

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
