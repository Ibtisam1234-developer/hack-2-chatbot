"""
FastAPI Application Entry Point for Todo API

Owner: Backend API Engineer
Purpose: Main FastAPI application with CORS, authentication, and database lifecycle
Architecture: Async FastAPI with SQLModel, JWT auth, and Neon PostgreSQL

Constitutional Constraints:
- REQUIRED: CORS configured for Next.js frontend (http://localhost:3000)
- REQUIRED: Database initialization on startup
- REQUIRED: Database cleanup on shutdown
- REQUIRED: Health check endpoint for monitoring
- REQUIRED: All routes protected with JWT authentication

Application Lifecycle:
1. Startup: Initialize database connection and create tables
2. Runtime: Handle API requests with JWT authentication
3. Shutdown: Close database connections gracefully

All endpoints enforce strict user isolation per constitution Principle IV.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db import init_database, cleanup_database, check_database_health
from src.api.routes import todos

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Startup:
    - Initialize database connection
    - Create tables if they don't exist
    - Verify database health

    Shutdown:
    - Close database connections
    - Release connection pool resources

    Args:
        app: FastAPI application instance

    Yields:
        None (context manager for lifespan)
    """
    # Startup
    logger.info("Starting Todo API application...")
    try:
        await init_database()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Todo API application...")
    try:
        await cleanup_database()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Todo API",
    description="Secure Todo API with JWT authentication and user isolation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Configure CORS for Next.js frontend
# CRITICAL: Must allow credentials for JWT token transmission
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development server
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,  # Required for JWT cookies/headers
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",  # JWT Bearer token
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With"
    ],
    expose_headers=["Content-Length", "Content-Type"],
    max_age=3600  # Cache preflight requests for 1 hour
)


# Include routers
app.include_router(todos.router)


# Health check endpoint (no authentication required)
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Health check endpoint",
    description="Check if the API and database are healthy. No authentication required.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"}
    }
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Checks:
    - API is running
    - Database connection is healthy

    Returns:
        dict: Health status with database connectivity

    Status Codes:
        200: Service is healthy
        503: Service is unhealthy (database connection failed)
    """
    try:
        # Check database connectivity
        db_healthy = await check_database_health()

        if not db_healthy:
            logger.error("Health check failed: Database connection unhealthy")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "database": "disconnected",
                    "message": "Database connection failed"
                }
            )

        return {
            "status": "healthy",
            "database": "connected",
            "message": "Todo API is running"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "error",
                "message": str(e)
            }
        )


# Root endpoint (no authentication required)
@app.get(
    "/",
    tags=["root"],
    summary="API root endpoint",
    description="Returns basic API information. No authentication required."
)
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API name, version, and documentation links
    """
    return {
        "name": "Todo API",
        "version": "1.0.0",
        "description": "Secure Todo API with JWT authentication and user isolation",
        "documentation": "/docs",
        "health": "/health"
    }


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.

    Logs the error and returns a generic 500 response.
    Prevents leaking sensitive information in error messages.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSONResponse: Generic error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error"
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn for development
    # Production: Use gunicorn with uvicorn workers
    uvicorn.run(
        "backend.src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )
