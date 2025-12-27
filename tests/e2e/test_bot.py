import pytest

import os
from telethon import TelegramClient


API_ID = os.getenv("TELEGRAM_API_ID")
if API_ID is not None: API_ID = int(API_ID)
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_NAME = os.getenv("BOT_USERNAME", "@N8NmazasaBot")


@pytest.mark.skipif(not API_ID, reason="No Telegram API creds")
@pytest.mark.asyncio
async def test_tc_f01_start_command():
    """TC-F01: Первичная авторизация (E2E)."""
    async with TelegramClient('e2e_sess', API_ID, API_HASH) as client:
        async with client.conversation(BOT_NAME, timeout=10) as conv:
            await conv.send_message("/start")
            resp = await conv.get_response()
            assert "Привет" in resp.text or "меню" in resp.text


@pytest.mark.skipif(not API_ID, reason="No Telegram API creds")
@pytest.mark.asyncio
async def test_tc_a01_settings_menu():
    """TC-A01: Проверка меню настроек."""
    async with TelegramClient('e2e_sess', API_ID, API_HASH) as client:
        async with client.conversation(BOT_NAME, timeout=10) as conv:
            await conv.send_message("/settings")
            resp = await conv.get_response()
            assert "Текущие категории" in resp.text


@pytest.mark.skipif(not API_ID, reason="No Telegram API creds")
@pytest.mark.asyncio
async def test_tc_a02_bad_file_format():
    """TC-A02: Реакция на некорректный файл (PDF/Doc)."""
    async with TelegramClient('e2e_sess', API_ID, API_HASH) as client:
        async with client.conversation(BOT_NAME, timeout=10) as conv:
            # Отправляем текстовый файл под видом PDF
            await conv.send_file("dummy.pdf", caption="Not excel")
            resp = await conv.get_response()
            assert "❌" in resp.text or "Excel" in resp.text