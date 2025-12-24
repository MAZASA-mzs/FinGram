import sys
import os
tests_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(tests_dir, '..')
sys.path.insert(0, project_root)

import pytest
from datetime import datetime, timedelta
from src.core.interfaces import Transaction, UserNote
from src.infrastructure.database.models import User, Note

@pytest.fixture
def mock_user():
    return User(
        id=1,
        telegram_id=12345,
        username="test_user",
        categories_list="Еда, Транспорт",
        custom_prompts="Подсказка"
    )

@pytest.fixture
def sample_transaction():
    return Transaction(
        date=datetime(2023, 10, 1),
        amount=500.0,
        description="Пятерочка",
        currency="RUB"
    )

@pytest.fixture
def sample_note():
    return Note(
        id=1,
        user_id=1,
        raw_text="Купил хлеб",
        created_at=datetime(2023, 10, 1)
    )

@pytest.fixture
def mock_transaction():
    return Transaction(
        date=datetime(2023, 10, 15, 12, 0, 0),
        amount=1000.0,
        description="Супермаркет",
        currency="RUB"
    )

@pytest.fixture
def sample_notes(mock_user):
    # Создаем заметки для BVA (Boundary Value Analysis)
    base_time = datetime(2023, 10, 15, 12, 0, 0)  # Время транзакции

    return [
        # 1. Точное совпадение (внутри окна)
        Note(id=1, user_id=mock_user.id, raw_text="Купил еду", created_at=base_time),

        # 2. Граница - ровно 2 дня назад (внутри окна)
        Note(id=2, user_id=mock_user.id, raw_text="Заметка на границе", created_at=base_time - timedelta(days=2)),

        # 3. За границей - 2 дня и 1 секунда назад (должно быть отброшено)
        Note(id=3, user_id=mock_user.id, raw_text="Старая заметка",
             created_at=base_time - timedelta(days=2, seconds=1)),

        # 4. Будущее - внутри окна (+1 день)
        Note(id=4, user_id=mock_user.id, raw_text="Заметка завтра", created_at=base_time + timedelta(days=1)),
    ]
