from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/oltinchain"

    # Redis
    redis_url: str = "redis://:password@localhost:6379/0"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # zkSync
    zksync_rpc_url: str = "https://sepolia.era.zksync.dev"
    oltin_contract_address: str = ""
    minter_private_key: str = ""

    # Gold Price
    gold_price_uzs_per_gram: int = 650_000
    fee_percent: float = 0.015  # 1.5% fee
    min_fee_uzs: int = 3_800
    spread_percent: float = 0.01  # 1% spread (0.5% each side)

    class Config:
        env_file = ".env"


settings = Settings()
