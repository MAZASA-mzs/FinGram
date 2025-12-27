import pytest
from unittest.mock import AsyncMock, MagicMock

import asyncio
import time
import datetime

from src.core.processor import Processor
from src.core.dtypes import Transaction


async def mock_heavy_processing(*args, **kwargs):
    """Эмуляция задержки LLM (0.5 сек)."""
    await asyncio.sleep(0.5)
    return {"category": "LoadTest", "comment": "Done"}


@pytest.mark.asyncio
async def test_tc_l01_concurrency_limit():
    ASYNC_SESSIONS_COUNT = 10

    # 1. Мокируем LLM
    mock_llm = AsyncMock()
    # Вместо лямбды попробуйте передать функцию напрямую
    mock_llm.categorize_transaction.side_effect = mock_heavy_processing

    # 2. Мокируем парсер
    mock_parser = MagicMock()
    mock_parser.parse.return_value = [Transaction(date=datetime.datetime.now(), amount=100, description="Load")]

    # 3. Исправляем мок базы данных
    mock_db = AsyncMock()

    # Чтобы db.execute(...).scalars().all() или подобные цепочки не падали:
    mock_result = MagicMock()
    # Если в коде вызывается .scalars(), возвращаем еще один мок
    mock_db.execute.return_value = mock_result
    mock_result.scalars.return_value.all.return_value = []  # Возвращаем пустой список заметок

    processor = Processor(
        parser=mock_parser,
        llm=mock_llm,
        report_gen=MagicMock(),
        window_days=1
    )

    # 4. Запускаем задачи, передавая наш mock_db
    start_time = time.time()
    tasks = []
    for _ in range(ASYNC_SESSIONS_COUNT):
        # Передаем mock_db вместо MagicMock()
        tasks.append(processor.process_statement(MagicMock(), "file.xlsx", mock_db))

    results = await asyncio.gather(*tasks)

    end_time = time.time()
    duration = end_time - start_time

    # Анализ
    assert len(results) == ASYNC_SESSIONS_COUNT
    # Если бы все шло последовательно: 0.5 * 10 = 5 сек.
    # Если параллельно (при одновременной обработке не более 4ёх запросов):
    # ~1.5 - 2.0 сек (с учетом оверхеда).
    # Проверяем, что работает асинхронно (быстрее 3 секунд)
    assert duration < 3.0