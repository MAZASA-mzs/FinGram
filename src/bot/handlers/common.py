from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
import os

from src.core.dtypes import ExportFile
from src.infrastructure.database.models import Note

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я FinGram.\n\n"
        "1. Пиши мне о тратах текстом: '500 кофе', '15000 продукты'.\n"
        "2. Раз в месяц скидывай Excel файл от Сбера.\n"
        "3. Настрой свои категории через /settings."
    )


@router.message(F.document)
async def handle_document(message: types.Message, user, db_session, bot, processor):
    doc = message.document
    if not (doc.file_name.endswith('.xlsx') or doc.file_name.endswith('.xls')):
        await message.answer("❌ Жду файл Excel (.xlsx).")
        return

    await message.answer("⏳ Анализирую выписку... Это может занять пару минут.")

    file = await bot.get_file(doc.file_id)
    file_path = f"data/temp_{doc.file_name}"
    await bot.download_file(file.file_path, file_path)

    try:
        report: ExportFile = await processor.process_statement(user, file_path, db_session)
        report_bytes = report.file_content
        report_ext = report.file_ext
        input_file = BufferedInputFile(
            report_bytes.read(),
            filename=f"report_{doc.file_name.split('.')[0]}.{report_ext}"
        )
        await message.answer_document(input_file, caption="✅ Твой отчет готов!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.message(F.text & ~F.text.startswith('/'))
async def handle_note(message: types.Message, user, db_session):
    """Принимает любой текст как заметку"""
    note = Note(
        user_id=user.id,
        raw_text=message.text,
        created_at=message.date
    )
    db_session.add(note)
    await db_session.commit()
    await message.answer("✍️ Запомнил.")