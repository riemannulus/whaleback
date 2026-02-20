import logging
from abc import ABC, abstractmethod
from datetime import date, datetime

import pandas as pd

from whaleback.api.krx_client import KRXClient
from whaleback.db.engine import get_session
from whaleback.db.models import CollectionLog


class BaseCollector(ABC):
    """Template Method pattern for all data collectors."""

    def __init__(self, client: KRXClient):
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, target_date: date) -> int:
        """Orchestrate: log_start -> fetch -> validate -> persist -> log_end."""
        date_str = target_date.strftime("%Y%m%d")
        self.logger.info(f"Collecting {self.collection_type} for {target_date}")

        with get_session() as session:
            self._log_start(session, target_date)

            try:
                df = self.fetch(date_str)
                if df is None or df.empty:
                    self.logger.warning(f"No data returned for {target_date}")
                    self._log_end(session, target_date, "success", 0)
                    return 0

                df = self.validate(df)
                if df.empty:
                    self.logger.warning(f"All data filtered out after validation for {target_date}")
                    self._log_end(session, target_date, "success", 0)
                    return 0

                count = self.persist(df, target_date, session)
                self.logger.info(f"Persisted {count} records for {target_date}")
                self._log_end(session, target_date, "success", count)
                return count

            except Exception as e:
                self.logger.error(f"Collection failed for {target_date}: {e}", exc_info=True)
                self._log_end(session, target_date, "failed", error=str(e))
                raise

    @property
    @abstractmethod
    def collection_type(self) -> str:
        ...

    @abstractmethod
    def fetch(self, date_str: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    @abstractmethod
    def persist(self, df: pd.DataFrame, target_date: date, session) -> int:
        ...

    def _log_start(self, session, target_date: date):
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(CollectionLog).values(
            collection_type=self.collection_type,
            target_date=target_date,
            status="running",
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_collection_type_date",
            set_={"status": "running", "started_at": datetime.now(), "error_message": None},
        )
        session.execute(stmt)
        session.flush()

    def _log_end(self, session, target_date: date, status: str, count: int = 0, error: str | None = None):
        log = (
            session.query(CollectionLog)
            .filter_by(collection_type=self.collection_type, target_date=target_date)
            .first()
        )
        if log:
            log.status = status
            log.records_count = count
            log.error_message = error
            log.completed_at = datetime.now()
            session.flush()
