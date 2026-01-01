"""OltinChain API main module."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.admin.router import router as admin_router
from app.api.auth.router import router as auth_router
from app.api.blockchain.router import router as blockchain_router
from app.api.bots.router import router as bots_router
from app.api.orderbook.router import router as orderbook_router
from app.api.orders.router import router as orders_router
from app.api.price.router import router as price_router
from app.api.reserves.router import router as reserves_router
from app.api.users.router import router as users_router
from app.api.wallet.router import router as wallet_router
from app.api.ws.router import router as ws_router
from app.application.services.broadcast_service import broadcast
from app.application.services.metrics_service import MetricsService
from app.config import settings
from app.database import async_session_maker
from app.infrastructure.blockchain import ZkSyncClient

logger = structlog.get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Background task handle
_metrics_task = None


async def broadcast_metrics_loop():
    """Background task to broadcast metrics every 10 seconds."""
    blockchain = ZkSyncClient()

    while True:
        try:
            async with async_session_maker() as session:
                metrics_service = MetricsService(session)
                metrics = await metrics_service.get_live_metrics()

                # Add total supply from blockchain
                try:
                    total_supply = await blockchain.get_total_supply()
                    metrics["total_supply"] = str(total_supply)
                except Exception as e:
                    logger.error("failed_to_get_total_supply", error=str(e))
                    metrics["total_supply"] = "0"

                await broadcast.broadcast_metrics(metrics)
                logger.debug("metrics_broadcast", metrics=metrics)

        except Exception as e:
            logger.error("metrics_broadcast_error", error=str(e))

        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _metrics_task
    logger.info("application_starting", version="0.1.0")

    # Start background metrics task
    _metrics_task = asyncio.create_task(broadcast_metrics_loop())
    logger.info("metrics_broadcast_task_started")

    yield

    # Cancel background task
    if _metrics_task:
        _metrics_task.cancel()
        try:
            await _metrics_task
        except asyncio.CancelledError:
            pass

    logger.info("application_shutdown")


app = FastAPI(
    title="OltinChain API",
    description="Gold-backed token platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(blockchain_router)
app.include_router(price_router)
app.include_router(orders_router)
app.include_router(wallet_router)
app.include_router(ws_router)
app.include_router(reserves_router)
app.include_router(admin_router)
app.include_router(bots_router)
app.include_router(orderbook_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/health/ready")
async def health_ready():
    """Readiness check endpoint."""
    # TODO: Check database and Redis connectivity
    return {"status": "ready"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "OltinChain API",
        "version": "0.1.0",
        "docs": "/docs",
    }
