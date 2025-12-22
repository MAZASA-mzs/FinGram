import asyncio
import logging
import os
import yaml
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.infrastructure.database.models import Base
from src.infrastructure.reporters.basic_csv import BasicCSVReportGenerator
from src.infrastructure.llm.ollama import OllamaProvider
from src.infrastructure.parsers.sber import SberParser
from src.core.processor import Processor
from src.bot.middlewares import AuthMiddleware
from src.bot.handlers import common, settings
from dotenv import load_dotenv


async def main():
    logging.basicConfig(level=logging.INFO)

    # 1. Загрузка конфигов
    load_dotenv('config/.env')  # грузит .env
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config_yaml = yaml.safe_load(f)

    # Объединяем конфиги для удобства
    config = {
        **config_yaml,
        'token': os.getenv("TELEGRAM_BOT_TOKEN"),
        'allowed_user_ids': os.getenv("ALLOWED_USER_IDS"),
        'ollama_url': os.getenv("OLLAMA_API_URL"),
        'ollama_model': os.getenv("OLLAMA_MODEL", "llama3"),
        'db_url': os.getenv("DATABASE_URL")
    }

    # 2. Инициализация инфраструктуры
    engine = create_async_engine(config['db_url'], echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Создаем таблицы (в проде лучше использовать Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Сборка зависимостей (DI)
    llm_provider = OllamaProvider(config['ollama_url'], config['ollama_model'])
    bank_parser = SberParser()
    report_gen = BasicCSVReportGenerator()

    processor = Processor(
        parser=bank_parser,
        llm=llm_provider,
        report_gen=report_gen,
        window_days=config['processing']['search_window_days']
    )

    # 4. Бот
    bot = Bot(token=config['token'])
    dp = Dispatcher()

    # Middleware
    dp.message.middleware(AuthMiddleware(async_session, config))

    # Внедряем зависимости в хендлеры
    # Простой способ DI через workflow_data
    dp["processor"] = processor
    dp["bot"] = bot

    # Роутеры
    dp.include_router(settings.router)
    dp.include_router(common.router)

    logging.info("🚀 Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())