"""Application configuration."""

from functools import lru_cache

from pydantic import PostgresDsn, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "OltinPay"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: PostgresDsn
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Telegram
    telegram_bot_token: SecretStr | None = None

    # CORS - stored as comma-separated string
    cors_origins_str: str = "http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    # Blockchain — zkSync Era Sepolia
    zksync_rpc_url: str = "https://sepolia.era.zksync.dev"
    zksync_chain_id: int = 300
    oltin_contract_address: str = "0x4A56B78DBFc2E6c914f5413B580e86ee1A474347"
    uzd_contract_address: str = "0x95b30Be4fdE1C48d7C5dC22C1EBA061219125A32"
    staking_contract_address: str = "0x63e537A3a150d06035151E29904C1640181C8314"
    admin_private_key: SecretStr | None = None

    # AI assistant (znai-cloud)
    znai_cloud_url: str | None = None
    znai_cloud_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
