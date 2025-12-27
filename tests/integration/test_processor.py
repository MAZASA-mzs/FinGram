import pytest
from unittest.mock import AsyncMock, MagicMock

from datetime import datetime

from src.core.processor import Processor
from src.core.dtypes import Transaction
from src.infrastructure.database.models import Note


@pytest.mark.asyncio
async def test_tc_u05_processor_context_window(db_session, test_user):
    """TC-U05: Смещение временного окна (связь заметки и транзакции)."""

    # 1. Создаем заметку: 1 января 10:00
    note_date = datetime(2024, 1, 1, 10, 0, 0)
    note = Note(user_id=test_user.id, raw_text="Купил молоко", created_at=note_date)
    db_session.add(note)
    await db_session.commit()

    # 2. Транзакция: 2 января 09:00 (разница < 24 часов, попадает в окно 1 день)
    tx_date = datetime(2024, 1, 2, 9, 0, 0)

    # 3. Мокаем зависимости
    mock_parser = MagicMock()
    mock_parser.parse.return_value = [
        Transaction(date=tx_date, amount=100, description="Supermarket")
    ]

    mock_llm = AsyncMock()
    # Мок ответа LLM
    mock_llm.categorize_transaction.return_value = {"category": "Еда", "comment": "Context used"}

    # 4. Запускаем процессор
    processor = Processor(
        parser=mock_parser,
        llm=mock_llm,
        report_gen=MagicMock(),
        window_days=1  # Окно 1 день
    )

    await processor.process_statement(test_user, "dummy.xlsx", db_session)

    # 5. Проверка: LLM вызван с заметкой "Купил молоко"
    call_args = mock_llm.categorize_transaction.call_args
    nearby_notes = call_args[1]['nearby_notes']  # kwargs['nearby_notes']

    assert len(nearby_notes) == 1
    assert nearby_notes[0].text == "Купил молоко"