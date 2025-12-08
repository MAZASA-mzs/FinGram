import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, BufferedInputFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from infrastructure.database.models import Base, User, Note
from infrastructure.implementations import SberParser, OllamaProvider
from core.processor import Processor
import yaml

# --- CONFIG & SETUP ---
logging.basicConfig(level=logging.INFO)

env_file_path = os.path.join(os.getcwd(), "config", ".env")
load_dotenv(dotenv_path=env_file_path)
# load_dotenv()
print(env_file_path)
print(os.getenv("TELEGRAM_BOT_TOKEN"))
print(os.getenv("OLLAMA_API_URL"))

# Загрузка конфига
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# DB Setup
engine = create_engine(config['database']['url'])
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Init Components
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

# Services
llm_provider = OllamaProvider(
    base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
    model=config['llm']['model_name']
)
bank_parser = SberParser()
processor = Processor(parser=bank_parser, llm=llm_provider)


# --- MIDDLEWARE (WHITELIST) ---
@dp.message.outer_middleware
async def whitelist_middleware(handler, event, data):
    user_id = event.from_user.id
    if user_id not in config['system']['whitelist']:
        await event.answer("⛔ Доступ запрещен. Ваш ID не в белом списке.")
        return

    # Добавляем сессию БД в хендлер
    with SessionLocal() as session:
        # Получаем или создаем пользователя
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            user = User(telegram_id=user_id, username=event.from_user.username)
            session.add(user)
            session.commit()
            session.refresh(user)

        data['db_session'] = session
        data['user'] = user
        return await handler(event, data)


# --- HANDLERS ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я FinGram.\n"
        "1. Просто пиши мне траты (например: '1500 такси до дома').\n"
        "2. Отправь мне файл выписки Сбербанка (.xlsx), и я категоризирую его.\n"
        "3. Настрой категории через /settings (пока не реализовано в MVP)."
    )


@dp.message(F.document)
async def handle_document(message: types.Message, db_session, user):
    """Обработка загрузки файла выписки"""
    doc = message.document

    # Простая проверка расширения
    if not (doc.file_name.endswith('.xlsx') or doc.file_name.endswith('.xls')):
        await message.answer("❌ Я понимаю только файлы Excel (.xlsx) от Сбера.")
        return

    await message.answer("📂 Файл получен. Начинаю анализ... Это может занять время.")

    # Скачивание файла
    file_id = doc.file_id
    file = await bot.get_file(file_id)
    file_path = f"data/{doc.file_name}"
    await bot.download_file(file.file_path, file_path)

    try:
        # Запуск процессора
        csv_buffer = await processor.process_statement(user, file_path, db_session)

        # Отправка результата
        result_file = BufferedInputFile(
            csv_buffer.getvalue().encode('utf-8'),
            filename=f"report_{doc.file_name}.csv"
        )
        await message.answer_document(result_file, caption="✅ Готово! Ваши категоризированные траты.")

    except Exception as e:
        logging.error(e)
        await message.answer(f"❌ Произошла ошибка при обработке: {str(e)}")
    finally:
        # Очистка (в продакшене лучше делать через background task)
        if os.path.exists(file_path):
            os.remove(file_path)


@dp.message(F.text)
async def handle_text_note(message: types.Message, db_session, user):
    """Сохранение текстовой заметки о трате"""
    note_text = message.text

    new_note = Note(
        user_id=user.id,
        raw_text=note_text,
        created_at=message.date  # Используем время сообщения
    )
    db_session.add(new_note)
    db_session.commit()

    await message.answer("✍️ Записал.")


# --- ENTRY POINT ---
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())