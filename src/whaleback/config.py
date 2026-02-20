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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
