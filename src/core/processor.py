import asyncio
from datetime import timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.interfaces import BaseBankParser, BaseLLMProvider, BaseReportGenerator
from src.core.dtypes import Transaction, UserNote, ExportFile
from src.infrastructure.database.models import User, Note


class Processor:
    def __init__(
            self,
            parser: BaseBankParser,
            llm: BaseLLMProvider,
            report_gen: BaseReportGenerator,
            window_days: int = 2,
            max_concurrency: int = 4  # Ограничение для локальной LLM
    ):
        self.parser = parser
        self.llm = llm
        self.report_gen = report_gen
        self.window_days = window_days
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _process_single_transaction(
            self,
            tx: Transaction,
            user: User,
            db: AsyncSession,
            categories: List[str],
            hints: str
    ):
        """Обработка одной транзакции внутри семафора."""

        # 1. Поиск заметок (быстрая операция с БД)
        window = timedelta(days=self.window_days)
        start_date = tx.date - window
        end_date = tx.date + window

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

        # 2. Обращение к LLM (медленная операция, требует семафор)
        async with self.semaphore:
            llm_result = await self.llm.categorize_transaction(
                transaction=tx,
                nearby_notes=nearby_notes,
                categories=categories,
                user_hints=hints
            )

        tx.category = llm_result.get('category', 'Разное')
        tx.comment = llm_result.get('comment', '')

    async def process_statement(self, user: User, file_path: str, db: AsyncSession) -> ExportFile:
        # 1. Парсинг
        if not self.parser.validate_format(file_path):
            raise ValueError("Формат файла не поддерживается.")

        transactions = self.parser.parse(file_path)
        categories = user.get_categories()
        hints = user.custom_prompts or ""

        # 2. Асинхронный запуск задач с ограничением конкурентности
        tasks = [
            self._process_single_transaction(tx, user, db, categories, hints)
            for tx in transactions
        ]

        # Ждем выполнения всех задач
        await asyncio.gather(*tasks)

        # 3. Генерация отчета
        return self.report_gen.generate(transactions)