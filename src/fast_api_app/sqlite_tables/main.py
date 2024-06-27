import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TableManager(ABC):
    def __init__(
        self,
        table_name: str,
        redis_key: str,
        cadence: int = 600,
        retry_cadence: int = 60,
    ):
        logger.info(f"Initializing TableManager for {table_name}")
        self.table_name = table_name
        self.redis_key = redis_key
        self.cadence = cadence
        self.retry_cadence = retry_cadence
        self.initialize_table()

    @abstractmethod
    def initialize_table(self) -> None:
        pass

    @abstractmethod
    def insert_data(self, data: dict) -> None:
        pass

    @abstractmethod
    def update_database(self) -> None:
        pass
