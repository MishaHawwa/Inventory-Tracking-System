"""
InvTrack - Inventory Tracking System
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.database.connection import init_db
from app.routers import products, transactions, reports, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="InvTrack - Inventory Tracking System",
    description="Real-time inventory management with product tracking, stock alerts, and reporting.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (JS, CSS, HTML frontend)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Register all routers
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend HTML."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "InvTrack API is running. Visit /docs for API documentation."}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "InvTrack"}
