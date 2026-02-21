from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="WB_",
    )

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "whaleback"
    db_user: str = "whaleback"
    db_password: str = "changeme"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # API
    krx_request_delay: float = 1.0
    krx_max_retries: int = 3
    krx_retry_backoff: float = 2.0

    # Scheduler
    schedule_hour: int = 18
    schedule_minute: int = 30
    timezone: str = "Asia/Seoul"

    # Backfill
    backfill_start_date: str = "20200101"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    # Cache
    cache_ttl: int = 300  # seconds

    # Analysis parameters
    risk_free_rate: float = 0.035  # Korean 10yr bond yield ~3.5%
    equity_risk_premium: float = 0.065  # Korea ERP ~6.5%
    whale_lookback_days: int = 20

    # Monte Carlo simulation
    simulation_num_paths: int = 10000
    simulation_min_history_days: int = 60
    simulation_max_sigma: float = 1.50

    # Analysis scheduler
    analysis_schedule_hour: int = 19
    analysis_schedule_minute: int = 0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
