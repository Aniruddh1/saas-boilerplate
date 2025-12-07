"""Extended health check utilities."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx
import redis.asyncio as aioredis
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health status."""

    status: HealthStatus
    version: str
    environment: str
    components: list[ComponentHealth] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "version": self.version,
            "environment": self.environment,
            "components": {
                c.name: {
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                    **c.details,
                }
                for c in self.components
            },
        }


async def check_database(db: AsyncSession) -> ComponentHealth:
    """Check database connectivity and latency."""
    start = time.time()
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        latency = (time.time() - start) * 1000

        return ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY if latency < 100 else HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message="Connected" if latency < 100 else "Slow response",
        )
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=str(e)[:100],
        )


async def check_redis(redis_url: str) -> ComponentHealth:
    """Check Redis connectivity and latency."""
    try:
        start = time.time()
        client = aioredis.from_url(redis_url)
        await client.ping()
        latency = (time.time() - start) * 1000
        await client.close()

        return ComponentHealth(
            name="redis",
            status=HealthStatus.HEALTHY if latency < 50 else HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message="Connected" if latency < 50 else "Slow response",
        )
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return ComponentHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=str(e)[:100],
        )


async def check_external_service(
    name: str,
    url: str,
    timeout: float = 5.0
) -> ComponentHealth:
    """Check external HTTP service health."""
    try:
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            latency = (time.time() - start) * 1000

            if response.status_code < 400:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    latency_ms=round(latency, 2),
                    details={"status_code": response.status_code},
                )
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    latency_ms=round(latency, 2),
                    message=f"HTTP {response.status_code}",
                )
    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=str(e)[:100],
        )


class HealthChecker:
    """
    Comprehensive health checker for the application.

    Usage:
        checker = HealthChecker(version="1.0.0", environment="production")
        checker.add_check("database", lambda: check_database(db))
        checker.add_check("redis", lambda: check_redis(redis_url))

        health = await checker.run()
    """

    def __init__(self, version: str, environment: str):
        self.version = version
        self.environment = environment
        self.checks: dict[str, callable] = {}

    def add_check(self, name: str, check_fn: callable) -> None:
        """Add a health check function."""
        self.checks[name] = check_fn

    async def run(self) -> SystemHealth:
        """Run all health checks concurrently."""
        results = await asyncio.gather(
            *[check() for check in self.checks.values()],
            return_exceptions=True
        )

        components = []
        for name, result in zip(self.checks.keys(), results):
            if isinstance(result, Exception):
                components.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)[:100],
                ))
            else:
                components.append(result)

        # Determine overall status
        statuses = [c.status for c in components]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return SystemHealth(
            status=overall,
            version=self.version,
            environment=self.environment,
            components=components,
        )

    async def run_quick(self) -> dict:
        """Run a quick health check (just status and version)."""
        return {
            "status": "healthy",
            "version": self.version,
            "environment": self.environment,
        }
