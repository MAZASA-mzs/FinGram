import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from src.models import Transaction, Note, Category
import datetime
import io
import logging
from typing import Optional

log = logging.getLogger(__name__)

async def generate_csv_report(session: AsyncSession, user_id: int, start_date: datetime.date, end_date: datetime.date) -> Optional[bytes]:
    """
    Генерирует CSV-отчет (в виде bytes) по транзакциям пользователя за период.
    Включает категорию, если транзакция сопоставлена.
    """
    log.info(f"Генерация отчета для {user_id} c {start_date} по {end_date}")

    try:
        # Добавляем 1 день к end_date, чтобы включить весь день
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)

        # Выбираем транзакции (только расходы)
        # И сразу подгружаем (JOIN) связанные заметки и их категории
        q = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.timestamp >= start_datetime,
            Transaction.timestamp <= end_datetime,
            Transaction.amount < 0
        ).options(
            joinedload(Transaction.matched_note).joinedload(Note.category)
        ).order_by(Transaction.timestamp.asc())

        result = await session.execute(q)
        transactions: list[Transaction] = result.scalars().unique().all() # unique() из-за JOIN

        if not transactions:
            log.warning("Транзакции за период не найдены.")
            return None

        # 2. Готовим данные для Pandas
        report_data = []
        for tx in transactions:
            category_name = "Без категории"
            note_text = ""

            if tx.matched_note and tx.matched_note.category:
                category_name = tx.matched_note.category.name
                note_text = tx.matched_note.text
            elif tx.matched_note:
                note_text = tx.matched_note.text
                category_name = "Заметка без категории (ИИ)" # Если заметка есть, но ИИ не смог

            report_data.append({
                "Дата": tx.timestamp.strftime("%Y-%m-%d"),
                "Время": tx.timestamp.strftime("%H:%M:%S"),
                "Сумма": tx.amount, # Отрицательная
                "Описание (Банк)": tx.description,
                "Категория": category_name,
                "Заметка (Пользователь)": note_text
            })

        # 3. Создаем DataFrame и CSV
        df = pd.DataFrame(report_data)

        # Используем io.BytesIO для сохранения в памяти
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig', sep=';')

        return output.getvalue()

    except Exception as e:
        log.error(f"Ошибка генерации отчета: {e}", exc_info=True)
        return None
