import pytest
import pytest_asyncio
import json as js
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.infrastructure.database.models import Base, User, Note
from datetime import datetime

# Используем in-memory SQLite для тестов
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    user = User(telegram_id=123456789, username="test_user")
    user.set_categories(["Еда", "Такси"])
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
def create_dummy_excel(tmp_path):
    """Создает временный Excel файл в формате Сбера"""
    def _create(filename="statement.xlsx"):
        data = {
            "Дата": ["01.01.2024", "02.01.2024"],
            "Сумма в валюте операции": [500.0, 1500.0],
            "Описание": ["Покупка в магазине", "Перевод"],
            "Валюта": ["RUB", "RUB"]
        }
        df = pd.read_json(js.dumps(data)) # Dummy conversion
        df = pd.DataFrame(data)
        # Добавляем пустые строки сверху, как в реальной выписке
        path = tmp_path / filename
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, startrow=3, index=False)
        return str(path)
    return _create