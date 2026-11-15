from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import ProcurementBaseException, domain_exception_handler
from backend.app.db.session import init_db
from backend.app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database schema
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    await init_db()
    logger.info("Application startup sequence completed.")
    yield
    # Shutdown
    logger.info("Application shutdown sequence initiated.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Agent AI Application for Evidence-Based Procurement Evaluation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register domain exception handlers
app.add_exception_handler(ProcurementBaseException, domain_exception_handler)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "api_version": "v1",
    }


@app.get("/", tags=["System"])
async def root():
    """Root entrypoint with service metadata."""
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }

