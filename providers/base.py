from abc import ABC, abstractmethod
from typing import List

from models.work_item import WorkItem


class BaseProvider(ABC):
    @abstractmethod
    async def fetch_items(self, start_date, end_date) -> List[WorkItem]:
        pass

    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass
