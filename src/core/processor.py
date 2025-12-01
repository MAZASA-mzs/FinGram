import csv
import io
from datetime import timedelta
from typing import List
from sqlalchemy.orm import Session

from src.core.interfaces import BaseBankParser, BaseLLMProvider, Transaction, UserNote
from src.infrastructure.database.models import User, Note


class Processor:
    def __init__(self, parser: BaseBankParser, llm: BaseLLMProvider):
        self.parser = parser
        self.llm = llm

    async def process_statement(self, user: User, file_path: str, db: Session) -> io.StringIO:
        """
        Основной пайплайн:
        1. Парсинг файла
        2. Выборка заметок из БД
        3. Запрос к LLM по каждой транзакции
        4. Генерация CSV
        """
        # 1. Парсинг
        if not self.parser.validate_format(file_path):
            raise ValueError("Неверный формат файла")

        transactions = self.parser.parse(file_path)

        # Подготовка CSV буфера
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Дата', 'Сумма', 'Описание Банка', 'Категория', 'Комментарий/Заметка'])

        # Получаем настройки пользователя
        categories = user.categories_list.split(',')
        hints = user.custom_prompts

        # 2. Обработка транзакций
        # В идеале это нужно делать асинхронно батчами, но для MVP сделаем цикл
        for tx in transactions:
            # Ищем заметки в окне +- 2 дня (настройка)
            window = timedelta(days=2)
            start_date = tx.date - window
            end_date = tx.date + window

            # Запрос к БД за заметками
            notes_db = db.query(Note).filter(
                Note.user_id == user.id,
                Note.created_at >= start_date,
                Note.created_at <= end_date
            ).all()

            nearby_notes = [
                UserNote(text=n.raw_text, timestamp=n.created_at, id=n.id)
                for n in notes_db
            ]

            # 3. LLM категоризация
            result = await self.llm.categorize_transaction(
                transaction=tx,
                nearby_notes=nearby_notes,
                categories=categories,
                user_hints=hints
            )

            tx.category = result.get('category', 'Не определено')
            tx.comment = result.get('comment', '')

            # Запись в CSV
            writer.writerow([
                tx.date.strftime("%Y-%m-%d"),
                tx.amount,
                tx.description,
                tx.category,
                tx.comment
            ])

        output.seek(0)
        return output