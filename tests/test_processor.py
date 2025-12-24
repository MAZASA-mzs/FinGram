import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from src.core.processor import Processor
from src.core.dtypes import UserNote


@pytest.mark.asyncio
async def test_processor_note_mapping_and_llm_call(mock_user, sample_transaction):
    """
    [Cause-Effect Analysis]
    Проверка корректного преобразования объектов БД Note в DTO UserNote.
    """
    mock_llm = AsyncMock()
    mock_llm.categorize_transaction.return_value = {"category": "Еда", "comment": "Ок"}

    # Мок объекта из БД (Note)
    db_note = MagicMock()
    db_note.id = 101
    db_note.raw_text = "Купил хлеб"  # Поле в модели БД
    db_note.created_at = datetime.now()

    # Настройка цепочки await db.execute() -> result.scalars().all()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [db_note]

    db_mock = AsyncMock()
    db_mock.execute.return_value = mock_result

    processor = Processor(MagicMock(), mock_llm, MagicMock())

    await processor._process_single_transaction(
        sample_transaction, mock_user, db_mock, ["Еда"], ""
    )

    # Проверка вызова LLM: был ли передан правильный DTO
    mock_llm.categorize_transaction.assert_called_once()
    kwargs = mock_llm.categorize_transaction.call_args.kwargs

    note_dto = kwargs['nearby_notes'][0]
    assert isinstance(note_dto, UserNote)
    assert note_dto.text == "Купил хлеб"  # Проверка маппинга из processor.py
    assert note_dto.id == 101