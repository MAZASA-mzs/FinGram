from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings
import logging

log = logging.getLogger(__name__)

# Создаем асинхронный "движок" для подключения к БД
# check_same_thread=False требуется только для SQLite
engine_args = {"echo": False}
if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}

try:
    engine = create_async_engine(settings.DATABASE_URL, **engine_args)

    # Создаем фабрику асинхронных сессий
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    log.info("Подключение к базе данных успешно настроено.")
except Exception as e:
    log.critical(f"Ошибка подключения к базе данных: {e}", exc_info=True)
    exit(1)


# Базовый класс для всех моделей SQLAlchemy
class Base(DeclarativeBase):
    pass


async def init_db():
    """
    Инициализирует базу данных: создает все таблицы,
    определенные через Base.
    """
    async with engine.begin() as conn:
        log.info("Инициализация таблиц в БД...")
        # await conn.run_sync(Base.metadata.drop_all) # Раскомментировать для сброса таблиц при отладке
        await conn.run_sync(Base.metadata.create_all)
    log.info("Инициализация таблиц завершена.")


async def get_db_session() -> AsyncSession:
    """
    Зависимость (dependency) для FastAPI и функция-генератор
    для получения сессии БД.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
