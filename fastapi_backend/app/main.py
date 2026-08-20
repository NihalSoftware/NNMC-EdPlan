import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import get_api_router
from app.core.config import settings
from app.db.session import engine
from app.student.api.router import get_student_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        version="1.0.0",
    )

    @app.get("/")
    async def root():
        return {
            "success": True,
            "message": "Northern New Mexico College Student Hub API is running",
            "data": {"name": settings.app_name, "version": "1.0.0"},
        }

    @app.get("/health/live", include_in_schema=False)
    async def liveness():
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness():
        if settings.disable_database:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "dependency": "database"},
            )
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.exception("Readiness check failed for database")
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "dependency": "database"},
            )
        return {"status": "ok"}

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = uuid.uuid4().hex
        logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
        payload = {
            "success": False,
            "message": "Internal server error",
            "request_id": request_id,
        }
        if settings.debug:
            payload["detail"] = str(exc)
        return JSONResponse(status_code=500, content=payload)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type"],
    )

    app.include_router(get_student_router())
    app.include_router(get_api_router())
    return app


app = create_application()
