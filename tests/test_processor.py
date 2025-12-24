import pytest
import io
import csv
from unittest.mock import MagicMock, AsyncMock
from src.core.processor import Processor
from src.core.interfaces import UserNote


@pytest.mark.asyncio
async def test_processor_workflow(mock_user, sample_transaction, sample_note):
    # --- 1. Mocks (Заглушки) ---

    # Мок парсера
    mock_parser = MagicMock()
    mock_parser.validate_format.return_value = True

    mock_parser.parse.return_value = [sample_transaction]

    # Мок LLM
    mock_llm = AsyncMock()
    mock_llm.categorize_transaction.return_value = {"category": "Тест", "comment": "Ок"}

    # Мок Базы Данных (Session)
    mock_db = MagicMock()
    # Сложная цепочка вызовов SQLAlchemy: db.query().filter().all()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.all.return_value = [sample_note]  # БД возвращает одну заметку

    # --- 2. Инициализация ---
    processor = Processor(parser=mock_parser, llm=mock_llm)

    # --- 3. Исполнение ---
    csv_buffer = await processor.process_statement(mock_user, "dummy.xlsx", mock_db)

    # --- 4. Проверки (Assertions) ---

    # А. Проверяем, что парсер вызвался
    mock_parser.parse.assert_called_once_with("dummy.xlsx")

    # Б. Проверяем, что LLM вызвалась с правильными данными
    # Мы должны убедиться, что заметка из БД попала в промпт
    args, _ = mock_llm.categorize_transaction.call_args

    # В. Проверяем итоговый CSV
    content = csv_buffer.getvalue()
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    assert rows[0] == ['Дата', 'Сумма', 'Описание Банка', 'Категория', 'Комментарий/Заметка']
    assert rows[1][3] == "Тест"  # Категория от LLM