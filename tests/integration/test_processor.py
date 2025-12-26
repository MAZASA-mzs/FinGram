import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from src.core.processor import Processor
from src.core.dtypes import Transaction
from src.infrastructure.database.models import Note


@pytest.mark.asyncio
async def test_processor_flow(db_session, test_user, create_dummy_excel):
    # 1. Подготовка данных
    # Создаем заметку в БД, которая должна попасть в "окно" поиска (2 дня)
    note_date = datetime(2024, 1, 1)  # Совпадает с первой транзакцией в dummy_excel
    note = Note(user_id=test_user.id, raw_text="Купил молоко", created_at=note_date)
    db_session.add(note)
    await db_session.commit()

    # 2. Моки
    mock_parser = MagicMock()
    # Возвращаем 1 транзакцию
    mock_parser.validate_format.return_value = True
    mock_parser.parse.return_value = [
        Transaction(date=datetime(2024, 1, 1), amount=100, description="Magazin")
    ]

    mock_llm = AsyncMock()
    # LLM возвращает категорию на основе заметки (имитация)
    mock_llm.categorize_transaction.return_value = {
        "category": "Еда",
        "comment": "Найдена заметка про молоко"
    }

    mock_reporter = MagicMock()
    mock_reporter.generate.return_value = MagicMock(file_content=b"CSV_DATA", file_ext="csv")

    # 3. Инициализация Processor
    processor = Processor(
        parser=mock_parser,
        llm=mock_llm,
        report_gen=mock_reporter,
        window_days=2
    )

    # 4. Запуск
    result = await processor.process_statement(test_user, "dummy.xlsx", db_session)

    # 5. Проверки
    # Проверяем, что LLM был вызван
    assert mock_llm.categorize_transaction.called

    # Проверяем аргументы вызова LLM: передалась ли заметка?
    call_args = mock_llm.categorize_transaction.call_args[1]
    nearby_notes = call_args['nearby_notes']
    assert len(nearby_notes) == 1
    assert nearby_notes[0].text == "Купил молоко"

    # Проверяем результат
    assert result.file_ext == "csv"