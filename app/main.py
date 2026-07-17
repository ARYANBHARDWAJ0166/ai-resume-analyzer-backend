import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .routes import resume_router, ai_analyzer_router
from .database import init_db
from .config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting AI Resume Analyzer API...")
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down AI Resume Analyzer API...")


# FastAPI app
app = FastAPI(
    title="AI Resume Analyzer API",
    description="Analyze resumes, match with jobs, and generate reports",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


# Global exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Resource not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"❌ Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "message": "Something went wrong. Please try again later."
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Unexpected error",
            "message": "Something went wrong. Please try again later."
        }
    )


# Include routers
app.include_router(resume_router, prefix="/api/v1")
app.include_router(ai_analyzer_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    return {
        "success": True,
        "message": "AI Resume Analyzer API is operational",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        # Check database
        from .database import SessionLocal
        db = SessionLocal()
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        db_status = "unhealthy"

    # Check Gemini API key
    gemini_status = "configured" if settings.GEMINI_API_KEY else "not configured"

    overall = "healthy" if db_status == "healthy" else "unhealthy"

    return {
        "success": True,
        "status": overall,
        "services": {
            "database": db_status,
            "gemini": gemini_status,
            "environment": settings.ENVIRONMENT
        }
    }