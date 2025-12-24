import pytest
from datetime import datetime
from src.infrastructure.database.models import User
from src.core.dtypes import Transaction

@pytest.fixture
def mock_user():
    user = User(
        id=1,
        telegram_id=12345,
        username="test_user",
        custom_prompts="Всегда классифицируй как Еда, если есть слово Хлеб"
    )
    user.set_categories(["Еда", "Транспорт", "ЖКХ"])
    return user

@pytest.fixture
def sample_transaction():
    return Transaction(
        date=datetime(2023, 10, 15, 12, 0),
        amount=1500.50,
        description="Супермаркет Магнит",
        currency="RUB"
    )