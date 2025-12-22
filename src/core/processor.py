import io
from datetime import timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.interfaces import BaseBankParser, BaseLLMProvider, BaseReportGenerator
from src.core.dtypes import Transaction, UserNote
from src.infrastructure.database.models import User, Note


class Processor:
    def __init__(
            self,
            parser: BaseBankParser,
            llm: BaseLLMProvider,
            report_gen: BaseReportGenerator,
            window_days: int = 2
    ):
        self.parser = parser
        self.llm = llm
        self.report_gen = report_gen
        self.window_days = window_days

    async def process_statement(self, user: User, file_path: str, db: AsyncSession) -> 3:
        # 1. Парсинг
        if not self.parser.validate_format(file_path):
            raise ValueError("Формат файла не поддерживается текущим парсером.")

        transactions = self.parser.parse(file_path)

        # 2. Обработка транзакций
        # Для оптимизации загружаем все заметки за весь период сразу, 
        # но для MVP оставим поиск по каждой транзакции для точности окна.

        categories = user.get_categories()
        hints = user.custom_prompts or ""

        for tx in transactions:
            window = timedelta(days=self.window_days)
            start_date = tx.date - window
            end_date = tx.date + window

            # Асинхронный запрос к БД
            result = await db.execute(
                select(Note).where(
                    Note.user_id == user.id,
                    Note.created_at >= start_date,
                    Note.created_at <= end_date
                )
            )
            notes_db = result.scalars().all()

            nearby_notes = [
                UserNote(id=n.id, text=n.raw_text, timestamp=n.created_at)
                for n in notes_db
            ]

            # LLM Classification
            llm_result = await self.llm.categorize_transaction(
                transaction=tx,
                nearby_notes=nearby_notes,
                categories=categories,
                user_hints=hints
            )

            tx.category = llm_result.get('category', 'Разное')
            tx.comment = llm_result.get('comment', '')

        # 3. Генерация отчета
        return self.report_gen.generate(transactions)