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

    # Blockchain — zkSync Era Sepolia (V3 contracts, see docs/DEPLOYMENTS.md)
    zksync_rpc_url: str = "https://sepolia.era.zksync.dev"
    zksync_chain_id: int = 300
    oltin_contract_address: str = "0x906bcf6c92ed1b30aA453c69eB40aeDbb3d5B3A5"
    uzd_contract_address: str = "0x51232fd0065bD2ca50551761Acef476E3CDf02aA"
    staking_contract_address: str = "0x63e537A3a150d06035151E29904C1640181C8314"
    exchange_address: str = "0x99D733E64eb60c3B3D5f3DeDe4CC4adC92BCd1c9"
    reserve_attestor_address: str = "0x9413F60295dcf7D81fcb69eE256029900B107d1B"
    xau_feed_address: str = "0xe0AFc7eD0c6028b8172C2b108624168d235e8BFD"
    uzs_feed_address: str = "0x637347fd661cFFAE9B562aFA394A392214fa24aD"
    # Legacy single admin key — retained for backwards compatibility only.
    # PR-2 server-side writes go through the role keys below (see SignerPool).
    admin_private_key: SecretStr | None = None

    # SignerPool role keys (each an independent EOA — one writer per key).
    # KEY_BANK_OPS = UZD mint/burn; KEY_RESERVE = ReserveAttestor.postAnswer;
    # KEY_UZS = UzsUsdFeed.postAnswer (keeper-uzs retired); KEY_XAU = external
    # keeper-xau only (the API never signs XAU — provided so Role.XAU resolves).
    key_bank_ops: SecretStr | None = None
    key_reserve: SecretStr | None = None
    key_uzs: SecretStr | None = None
    key_xau: SecretStr | None = None

    # Bank connector HMAC auth (X-Bank-Signature = HMAC-SHA256 over body+ts+nonce)
    bank_hmac_secret: SecretStr | None = None
    bank_hmac_max_skew_sec: int = 300  # reject timestamps older/newer than this

    # Chain indexer (simple last-N poller; not reorg-safe, testnet demo only)
    indexer_enabled: bool = True
    indexer_poll_sec: int = 15
    indexer_lookback_blocks: int = 5000

    # AI assistant (znai-cloud)
    znai_cloud_url: str | None = None
    znai_cloud_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
