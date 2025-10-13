from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from src.models import Transaction, Note
import datetime
import logging
from typing import List

log = logging.getLogger(__name__)

# Временное окно для сопоставления (в минутах)
MATCH_WINDOW_MINUTES = 15

async def find_and_match_transactions(session: AsyncSession, user_id: int) -> int:
    """
    Ищет несопоставленные транзакции и заметки для пользователя
    и пытается их сопоставить.

    Логика v1 (MVP):
    1. Берем все транзакции (Т) без `matched_note_id`.
    2. Берем все заметки (З) без `matched_transaction_id`.
    3. Для каждой Т ищем З в окне +/- 15 минут.
    4. Если найдена ровно ОДНА З - сопоставляем.
    5. Если найдено 0 или >1 - пропускаем (оставляем для v2).

    Возвращает количество выполненных сопоставлений.
    """
    log.info(f"Запуск сервиса сопоставления для пользователя {user_id}...")

    try:
        # 1. Получаем несопоставленные транзакции
        q_trans = await session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.matched_note_id == None,
                Transaction.amount < 0 # Только расходы
            ).order_by(Transaction.timestamp)
        )
        unmatched_transactions: List[Transaction] = q_trans.scalars().all()

        # 2. Получаем несопоставленные заметки
        q_notes = await session.execute(
            select(Note).where(
                Note.user_id == user_id,
                Note.matched_transaction_id == None
            ).order_by(Note.timestamp)
        )
        unmatched_notes: List[Note] = q_notes.scalars().all()

        if not unmatched_transactions or not unmatched_notes:
            log.info("Нет транзакций или заметок для сопоставления.")
            return 0

        match_count = 0

        # Конвертируем список заметок в set для быстрого удаления
        # (чтобы не сопоставить одну заметку дважды)
        available_notes = set(unmatched_notes)

        # 3. Для каждой транзакции ищем заметку
        for tx in unmatched_transactions:
            time_start = tx.timestamp - datetime.timedelta(minutes=MATCH_WINDOW_MINUTES)
            time_end = tx.timestamp + datetime.timedelta(minutes=MATCH_WINDOW_MINUTES)

            # Ищем в *еще не использованных* заметках
            potential_matches: List[Note] = []
            for note in available_notes:
                if time_start <= note.timestamp <= time_end:
                    potential_matches.append(note)

            # 4. Если найдена ровно одна - сопоставляем
            if len(potential_matches) == 1:
                matched_note = potential_matches[0]

                log.info(f"Сопоставление (1-к-1): TX({tx.id}, {tx.description}, {tx.timestamp}) <-> Note({matched_note.id}, {matched_note.text}, {matched_note.timestamp})")

                # Связываем их
                tx.matched_note_id = matched_note.id
                matched_note.matched_transaction_id = tx.id

                # Убираем заметку из пула доступных
                available_notes.remove(matched_note)
                match_count += 1

            # 5. Если 0 или >1
            elif len(potential_matches) > 1:
                # TODO: Логика v2 (Ollama или "ближайший по времени")
                # Для MVP v1 - пропускаем.
                log.info(f"Пропуск TX({tx.id}): Найдено {len(potential_matches)} заметок в окне.")
            else:
                # 0 заметок
                pass

        if match_count > 0:
            await session.commit()

        log.info(f"Сопоставление завершено. Новых пар: {match_count}")
        return match_count

    except Exception as e:
        log.error(f"Ошибка в matching_service: {e}", exc_info=True)
        await session.rollback()
        raise
