import pytest
from unittest.mock import AsyncMock, patch

from datetime import datetime
from aiogram.types import Message, Chat, User as TgUser

from src.bot.middlewares import AuthMiddleware


@pytest.mark.asyncio
async def test_tc_f02_access_denied():
    """TC-F02: Ограничение несанкционированного доступа."""
    config = {
        'allowed_user_ids': '111,222',
        'defaults': {
            'categories': ['Еда'],
            'llm_hints': ''
        }
    }
    middleware = AuthMiddleware(session_maker=AsyncMock(), config=config)

    # Приходит User ID 999 (чужой)
    event = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=999, type='private'),
        from_user=TgUser(id=999, is_bot=False, first_name="Hacker", username="hacker"),
        text="/start"
    )

    handler = AsyncMock()

    # Мокаем ответ бота
    with patch.object(Message, 'answer', new_callable=AsyncMock) as mock_answer:
        await middleware(handler, event, {})

        # Проверяем, что хендлер НЕ вызван
        handler.assert_not_called()
        # Проверяем сообщение об отказе
        mock_answer.assert_called_with("⛔ Нет доступа.")


@pytest.mark.asyncio
async def test_access_granted(db_engine):
    """Проверка успешного доступа."""
    # И снова такого теста не было, но мне захотелось добавить
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    config = {
        'allowed_user_ids': '333',
        'defaults': {
            'categories': ["Def"],
            'llm_hints': ''
        }
    }
    middleware = AuthMiddleware(session_maker=session_maker, config=config)

    event = Message(
        message_id=2,
        date=datetime.now(),
        chat=Chat(id=333, type='private'),
        from_user=TgUser(id=333, is_bot=False, first_name="Valid", username="valid_user"),
        text="test"
    )
    handler = AsyncMock()
    data = {}

    await middleware(handler, event, data)

    # Хендлер вызван, сессия прокинута
    handler.assert_called_once()
    assert 'db_session' in data