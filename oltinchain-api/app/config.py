"""Application configuration."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with secure defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/oltinchain"

    # Redis
    redis_url: str = "redis://:password@localhost:6379/0"

    # Security - NO DEFAULT for secret_key (must be in .env)
    secret_key: SecretStr
    access_token_expire_minutes: int = 15  # 15 minutes (was 1440!)
    refresh_token_expire_days: int = 7

    # CORS - allowed origins (string, parsed to list)
    cors_origins_str: str = (
        "https://app.oltinchain.com,https://dashboard.oltinchain.com,https://oltinchain.com"
    )

    # zkSync
    zksync_rpc_url: str = "https://sepolia.era.zksync.dev"
    oltin_contract_address: str = ""
    minter_private_key: SecretStr = SecretStr("")

    # Gold Price
    gold_price_uzs_per_gram: int = 650_000
    fee_percent: float = 0.015  # 1.5% fee
    min_fee_uzs: int = 3_800
    spread_percent: float = 0.01  # 1% spread (0.5% each side)

    # Debug mode
    debug: bool = False

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]


settings = Settings()
