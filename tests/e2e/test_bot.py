import pytest
import os
from telethon import TelegramClient
from telethon.tl.custom.message import Message

# Данные берутся из переменных окружения (безопасность)
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_NAME = os.getenv("BOT_USERNAME", "@FinGramTestBot")


@pytest.mark.skipif(not API_ID, reason="No Telegram API creds")
@pytest.mark.asyncio
async def test_start_command():
    async with TelegramClient('anon', API_ID, API_HASH) as client:
        async with client.conversation(BOT_NAME, timeout=10) as conv:
            # Отправляем /start
            await conv.send_message("/start")

            # Получаем ответ
            resp: Message = await conv.get_response()

            # Проверяем текст ответа (см. common.py)
            assert "Привет! Я FinGram" in resp.text
            assert "Настрой свои категории" in resp.text


@pytest.mark.skipif(not API_ID, reason="No Telegram API creds")
@pytest.mark.asyncio
async def test_settings_flow():
    async with TelegramClient('anon', API_ID, API_HASH) as client:
        async with client.conversation(BOT_NAME, timeout=10) as conv:
            await conv.send_message("/settings")
            resp = await conv.get_response()
            assert "Текущие категории" in resp.text

            # Пробуем изменить категории
            await conv.send_message("/set_cats Еда, Тесты")
            resp_confirm = await conv.get_response()
            assert "Категории обновлены" in resp_confirm.text