"""OltinPay API application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from src.auth.router import router as auth_router
from src.aylin.router import router as aylin_router
from src.balances.router import router as balances_router
from src.config import settings
from src.contacts.router import router as contacts_router
from src.database import engine
from src.staking.router import router as staking_router
from src.transfers.router import router as transfers_router
from src.users.router import router as users_router
from src.welcome.router import router as welcome_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        description="Telegram Mini App for tokenized gold trading",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    prefix = settings.api_v1_prefix

    app.include_router(auth_router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(users_router, prefix=f"{prefix}/users", tags=["users"])
    app.include_router(balances_router, prefix=f"{prefix}/balances", tags=["balances"])
    app.include_router(
        transfers_router, prefix=f"{prefix}/transfers", tags=["transfers"]
    )
    app.include_router(staking_router, prefix=f"{prefix}/staking", tags=["staking"])
    app.include_router(welcome_router, prefix=f"{prefix}/welcome", tags=["welcome"])
    app.include_router(contacts_router, prefix=f"{prefix}/contacts", tags=["contacts"])
    app.include_router(aylin_router, prefix=f"{prefix}/aylin", tags=["aylin"])

    return app


app = create_app()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"name": settings.app_name, "version": "0.1.0"}
