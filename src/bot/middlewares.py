from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.infrastructure.database.models import User
import yaml


class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_maker, config):
        self.session_maker = session_maker
        self.allowed_ids = [int(x) for x in str(config['allowed_user_ids']).split(',')]
        self.default_categories = config['defaults']['categories']
        self.default_hints = config['defaults']['llm_hints']

    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user_id = event.from_user.id

            if user_id not in self.allowed_ids:
                await event.answer("⛔ Нет доступа.")
                return

            async with self.session_maker() as session:
                user = await session.scalar(
                    select(User).where(User.telegram_id == user_id)
                )

                if not user:
                    user = User(
                        telegram_id=user_id,
                        username=event.from_user.username,
                        custom_prompts=self.default_hints
                    )
                    user.set_categories(self.default_categories)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)

                data['db_session'] = session
                data['user'] = user
                return await handler(event, data)
        return await handler(event, data)