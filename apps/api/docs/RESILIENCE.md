# Resilience & Observability

Patterns for building resilient, observable APIs.

## Overview

| Pattern | Purpose | Location |
|---------|---------|----------|
| **Rate Limiting** | Prevent API abuse | `src/api/middleware/rate_limit.py` |
| **Idempotency** | Safe retries | `src/utils/idempotency.py` |
| **Request Context** | Distributed tracing | `src/utils/context.py` |
| **Health Checks** | Liveness/readiness | `src/utils/health.py` |

---

## Rate Limiting

Prevents API abuse with per-user/IP limits using Redis sliding window.

### Global Rate Limit (Middleware)

```python
# In main.py
from src.api.middleware.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, redis_client=redis)
```

Configuration:
```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100      # Max requests per window
RATE_LIMIT_WINDOW=60         # Window in seconds
```

### Per-Endpoint Rate Limit

```python
from src.api.middleware.rate_limit import rate_limit

@router.post("/expensive-operation")
@rate_limit(max_requests=5, window_seconds=60)
async def expensive_endpoint():
    ...
```

### Response Headers

All responses include rate limit info:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 45
```

When rate limited (429):
```json
{
  "detail": "Too many requests",
  "retry_after": 45
}
```

---

## Idempotency Keys

Ensures operations can be safely retried without side effects.

**Critical for:**
- Payment processing
- Order creation
- Webhook handlers
- Any non-idempotent operation

### Client Usage

```bash
# First request - processed
curl -X POST /api/payments \
  -H "Idempotency-Key: pay_abc123" \
  -d '{"amount": 100}'

# Retry - returns cached response (no duplicate payment)
curl -X POST /api/payments \
  -H "Idempotency-Key: pay_abc123" \
  -d '{"amount": 100}'
```

### Dependency Pattern (Recommended)

```python
from src.utils.idempotency import IdempotencyGuard, get_idempotency_guard
from fastapi.responses import JSONResponse

@router.post("/payments")
async def create_payment(
    data: PaymentCreate,
    idem: IdempotencyGuard = Depends(get_idempotency_guard),
):
    # Check for duplicate
    result = await idem.check()
    if result.is_duplicate:
        return JSONResponse(
            content=result.cached_response,
            status_code=result.cached_status_code,
            headers={"X-Idempotent-Replayed": "true"},
        )

    # Mark as processing
    await idem.start("create_payment")

    try:
        # Process payment
        payment = await process_payment(data)

        # Cache successful response
        await idem.complete(payment.dict())

        return payment
    except Exception as e:
        await idem.fail(str(e))
        raise
```

### Decorator Pattern (Simple)

```python
from src.utils.idempotency import idempotent

@router.post("/payments")
@idempotent(ttl=86400, require_key=True)
async def create_payment(request: Request, data: PaymentCreate):
    return await process_payment(data)
```

### Require Idempotency Key

```python
from src.utils.idempotency import require_idempotency_key

@router.post("/payments")
async def create_payment(
    key: str = Depends(require_idempotency_key),
):
    # Key is required, 400 if missing
    ...
```

### Generate Deterministic Keys

```python
from src.utils.idempotency import generate_idempotency_key

# Generate key from operation parameters
key = generate_idempotency_key(
    "create_payment",
    user_id,
    amount,
    currency,
)
# "a1b2c3d4e5f6..."
```

---

## Request Context (Correlation IDs)

Track requests across services and correlate logs.

### Setup Middleware

```python
# In main.py
from src.utils.context import RequestContextMiddleware

app.add_middleware(RequestContextMiddleware)
```

### Automatic Propagation

Incoming request:
```
X-Correlation-ID: abc123  (optional, generated if missing)
```

Response headers (automatic):
```
X-Request-ID: req_xyz789
X-Correlation-ID: abc123
```

### Access Context Anywhere

```python
from src.utils.context import (
    get_correlation_id,
    get_request_id,
    get_request_context,
)

@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    # Access correlation ID for logging
    correlation_id = get_correlation_id()
    logger.info("Fetching order",
        order_id=order_id,
        correlation_id=correlation_id,
    )

    # Full context
    ctx = get_request_context()
    # ctx.request_id, ctx.correlation_id, ctx.user_id, etc.
```

### Set User Context (Auth Middleware)

```python
from src.utils.context import set_context_user

# In your auth middleware
async def auth_middleware(request, call_next):
    user = await authenticate(request)
    set_context_user(str(user.id), str(user.tenant_id))
    return await call_next(request)
```

### Propagate to Downstream Services

```python
import httpx
from src.utils.context import get_tracing_headers

async def call_other_service():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://order-service/api/orders",
            headers=get_tracing_headers(),
        )
```

### Structlog Integration

```python
import structlog
from src.utils.context import add_request_context

structlog.configure(
    processors=[
        add_request_context,  # Auto-adds correlation_id to all logs
        structlog.processors.JSONRenderer(),
    ]
)

# All logs now include correlation_id automatically
logger.info("Processing order")
# {"event": "Processing order", "correlation_id": "abc123", ...}
```

### Background Tasks

```python
from src.utils.context import copy_context, restore_context

# Copy context before spawning background task
ctx = copy_context()

async def background_job():
    restore_context(ctx)  # Restore correlation ID
    correlation_id = get_correlation_id()
    # Logs will have same correlation_id
```

---

## Health Checks

Monitor application and dependency health.

### Quick Health (Liveness)

```python
from src.utils.health import HealthChecker

checker = HealthChecker(version="1.0.0", environment="production")

@router.get("/health")
async def health():
    return await checker.run_quick()
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### Full Health (Readiness)

```python
from src.utils.health import (
    HealthChecker,
    check_database,
    check_redis,
)

checker = HealthChecker(version="1.0.0", environment="production")
checker.add_check("database", lambda: check_database(db))
checker.add_check("redis", lambda: check_redis(redis_url))

@router.get("/health/ready")
async def readiness():
    health = await checker.run()
    status_code = 200 if health.status == "healthy" else 503
    return JSONResponse(health.to_dict(), status_code=status_code)
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.5,
      "message": "Connected"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.2,
      "message": "Connected"
    }
  }
}
```

### Custom Health Checks

```python
from src.utils.health import ComponentHealth, HealthStatus

async def check_external_api() -> ComponentHealth:
    try:
        response = await client.get("https://api.example.com/health")
        return ComponentHealth(
            name="external_api",
            status=HealthStatus.HEALTHY,
            latency_ms=response.elapsed.total_seconds() * 1000,
        )
    except Exception as e:
        return ComponentHealth(
            name="external_api",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        )

checker.add_check("external_api", check_external_api)
```

### Kubernetes Probes

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Best Practices

### Rate Limiting

1. **Start conservative** - Begin with lower limits, increase as needed
2. **Different limits per tier** - Premium users get higher limits
3. **Skip internal paths** - Don't rate limit health checks, metrics
4. **Return helpful headers** - Help clients implement backoff

### Idempotency

1. **Always for payments** - Financial operations must be idempotent
2. **Client generates keys** - Let clients control the key
3. **Scope by user** - Keys are namespaced to prevent collisions
4. **Cache long enough** - 24 hours is typical for payment retries

### Request Context

1. **Propagate to all services** - Include correlation ID in outgoing requests
2. **Log with context** - Every log should include correlation ID
3. **Background tasks** - Copy context before spawning tasks

### Health Checks

1. **Separate liveness/readiness** - Liveness simple, readiness comprehensive
2. **Set timeouts** - Don't let health checks hang
3. **Include dependencies** - Check database, cache, external services
4. **Return status codes** - 200 for healthy, 503 for unhealthy
