from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaction:
    date: datetime
    amount: float
    description: str
    currency: str = "RUB"
    category: Optional[str] = None  # Заполняется LLM
    comment: Optional[str] = None  # Заполняется LLM


@dataclass
class UserNote:
    text: str
    timestamp: datetime
    id: int


class BaseBankParser(ABC):
    """Интерфейс для парсеров банковских выписок"""

    @abstractmethod
    def parse(self, file_path: str) -> List[Transaction]:
        """Принимает путь к файлу, возвращает список транзакций"""
        pass

    @abstractmethod
    def validate_format(self, file_path: str) -> bool:
        """Проверяет, подходит ли формат файла этому парсеру"""
        pass


class BaseLLMProvider(ABC):
    """Интерфейс для взаимодействия с LLM"""

    @abstractmethod
    async def categorize_transaction(
            self,
            transaction: Transaction,
            nearby_notes: List[UserNote],
            categories: List[str],
            user_hints: str
    ) -> dict:
        """
        Возвращает словарь вида {'category': str, 'comment': str}.
        Здесь происходит магия сопоставления.
        """
        pass