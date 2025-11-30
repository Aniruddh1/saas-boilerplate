"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.container import container
from src.core.hooks.manager import hooks
from src.api.routes import router as api_router
from src.api.middleware.logging import LoggingMiddleware
from src.api.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    # Register backend implementations
    from src.implementations.register import register_backends
    register_backends()

    container.configure(settings.get_backends_config())
    await container.initialize()
    await hooks.trigger("app.startup")

    yield

    # Shutdown
    await hooks.trigger("app.shutdown")
    await container.shutdown()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # Middleware (order matters - first added is outermost)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(api_router, prefix="/api")

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler."""
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": str(exc) if settings.debug else "An error occurred",
            },
        )

    # Health checks
    @app.get("/health")
    async def health_check():
        """Quick health check endpoint (for load balancers)."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
        }

    @app.get("/health/detailed")
    async def health_check_detailed():
        """
        Detailed health check with component status.

        Checks database, redis, and other services.
        """
        from src.utils.health import HealthChecker, check_database, check_redis
        from src.models.database import async_session_factory

        checker = HealthChecker(
            version=settings.app_version,
            environment=settings.environment,
        )

        # Add database check
        async def db_check():
            async with async_session_factory() as session:
                return await check_database(session)

        checker.add_check("database", db_check)

        # Add redis check
        checker.add_check("redis", lambda: check_redis(str(settings.redis.url)))

        health = await checker.run()
        status_code = 200 if health.status.value == "healthy" else 503

        from fastapi.responses import JSONResponse
        return JSONResponse(content=health.to_dict(), status_code=status_code)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )
