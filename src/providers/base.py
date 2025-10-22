from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generator

from models.work_item import WorkItem


class BaseProvider(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the provider.
        """

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is configured, i.e. all necessary settings are in place to run sync.
        """

    @abstractmethod
    def setup(self):
        """
        Implement setup logic for the provider
        """

    @abstractmethod
    def authenticate(self):
        """
        Validate connection with provider by using a simple API call.
        """

    @abstractmethod
    def fetch_items(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> Generator[WorkItem, None, None]:
        pass
