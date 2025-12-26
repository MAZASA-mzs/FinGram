import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from aiogram.types import Message, Chat, User

from src.bot.middlewares import AuthMiddleware


@pytest.mark.asyncio
async def test_auth_middleware_access_denied():
    config = {'allowed_user_ids': '111,222', 'defaults': {'categories': [], 'llm_hints': ''}}
    middleware = AuthMiddleware(session_maker=AsyncMock(), config=config)

    event = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=999, type='private'),
        from_user=User(id=999, is_bot=False, first_name="Stranger"),
        text="test"
    )

    handler = AsyncMock()
    data = {}

    # Патчим метод answer прямо в классе Message для этого конкретного объекта
    with patch.object(Message, 'answer', new_callable=AsyncMock) as mock_answer:
        await middleware(handler, event, data)

        handler.assert_not_called()
        mock_answer.assert_called_with("⛔ Нет доступа.")


@pytest.mark.asyncio
async def test_auth_middleware_access_granted(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    config = {'allowed_user_ids': '333', 'defaults': {'categories': ["Def"], 'llm_hints': ''}}
    middleware = AuthMiddleware(session_maker=session_maker, config=config)

    event = Message(
        message_id=2,
        date=datetime.now(),
        chat=Chat(id=333, type='private'),
        from_user=User(id=333, is_bot=False, first_name="Valid", username="valid_user"),
        text="test"
    )

    handler = AsyncMock()
    data = {}

    await middleware(handler, event, data)

    handler.assert_called_once()
    assert 'db_session' in data
    assert data['user'].telegram_id == 333