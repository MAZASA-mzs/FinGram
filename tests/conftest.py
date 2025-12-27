import io
import pytest
import pytest_asyncio
import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.infrastructure.database.models import Base, User

# In-memory SQLite для тестов
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Создает движок БД на время теста."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Предоставляет сессию для каждого теста с откатом изменений."""
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        # Автоматический rollback не требуется, т.к. in-memory, но полезно для чистоты
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Создает базового пользователя для тестов."""
    user = User(telegram_id=123456789, username="test_unit_user")
    user.set_categories(["Еда", "Транспорт", "Здоровье"])
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def create_dummy_excel(tmp_path):
    """Генератор Excel-файлов для тестов парсера."""

    def _create(filename="statement.xlsx", data=None):
        if data is None:
            data = {
                "Дата": ["01.01.2024", "02.01.2024"],
                "Сумма в валюте операции": [500.0, 1500.0],
                "Описание": ["Покупка Продукты", "Перевод Такси"],
                "Валюта": ["RUB", "RUB"]
            }

        df = pd.DataFrame(data)
        path = tmp_path / filename
        # Используем engine openpyxl, так как это стандарт для xlsx
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, startrow=3, index=False)  # Эмуляция "шапки" банка
        return str(path)

    return _create