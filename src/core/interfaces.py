from abc import ABC, abstractmethod
from typing import List
import io
from src.core.dtypes import Transaction, UserNote

class BaseBankParser(ABC):
    """Интерфейс для парсеров банковских выписок"""
    @abstractmethod
    def validate_format(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def parse(self, file_path: str) -> List[Transaction]:
        pass

class BaseLLMProvider(ABC):
    """Интерфейс для AI-провайдеров"""
    @abstractmethod
    async def categorize_transaction(
            self,
            transaction: Transaction,
            nearby_notes: List[UserNote],
            categories: List[str],
            user_hints: str
    ) -> dict:
        """Должен возвращать dict {'category': str, 'comment': str}"""
        pass

class BaseReportGenerator(ABC):
    """Интерфейс для генерации выходных отчетов"""
    @abstractmethod
    def generate(self, transactions: List[Transaction]) -> io.BytesIO:
        """Возвращает байтовый поток файла"""
        pass