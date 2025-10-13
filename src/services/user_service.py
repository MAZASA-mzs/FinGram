from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import User
import logging

log = logging.getLogger(__name__)

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None) -> User:
    """
    Находит пользователя по telegram_id или создает нового,
    если он не найден.
    """
    try:
        # Пытаемся найти пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Обновляем username, если он изменился
            if username and user.username != username:
                user.username = username
                await session.commit()
            return user
        else:
            # Создаем нового пользователя
            log.info(f"Создание нового пользователя: {telegram_id} ({username})")
            new_user = User(telegram_id=telegram_id, username=username)
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return new_user
    except Exception as e:
        log.error(f"Ошибка в get_or_create_user для {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        raise
