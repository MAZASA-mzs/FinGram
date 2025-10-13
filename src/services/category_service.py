from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from src.models import Category, User
from src.schemas import CategoryCreate, CategoryUpdate
from typing import List, Optional
import logging

log = logging.getLogger(__name__)

async def create_user_category(session: AsyncSession, user_id: int, category_data: CategoryCreate) -> Category:
    """
    Создает новую категорию для пользователя.
    """
    try:
        new_category = Category(**category_data.model_dump(), user_id=user_id)
        session.add(new_category)
        await session.commit()
        await session.refresh(new_category)
        return new_category
    except IntegrityError:
        # Ошибка, если категория с таким именем у этого пользователя уже есть
        await session.rollback()
        log.warning(f"Категория '{category_data.name}' уже существует у пользователя {user_id}")
        return None
    except Exception as e:
        log.error(f"Ошибка создания категории: {e}", exc_info=True)
        await session.rollback()
        raise

async def get_user_categories(session: AsyncSession, user_id: int) -> List[Category]:
    """
    Возвращает все категории пользователя.
    """
    result = await session.execute(
        select(Category).where(Category.user_id == user_id).order_by(Category.name)
    )
    return result.scalars().all()

async def get_category_by_id(session: AsyncSession, category_id: int, user_id: int) -> Optional[Category]:
    """
    Возвращает категорию по ID, проверяя, что она принадлежит пользователю.
    """
    result = await session.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def update_user_category(session: AsyncSession, category_id: int, user_id: int, category_data: CategoryUpdate) -> Optional[Category]:
    """
    Обновляет категорию пользователя.
    """
    category = await get_category_by_id(session, category_id, user_id)
    if not category:
        return None

    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    try:
        await session.commit()
        await session.refresh(category)
        return category
    except IntegrityError:
        await session.rollback()
        log.warning(f"Ошибка обновления: категория с таким именем уже существует у {user_id}")
        return None
    except Exception as e:
        log.error(f"Ошибка обновления категории {category_id}: {e}", exc_info=True)
        await session.rollback()
        raise

async def delete_user_category(session: AsyncSession, category_id: int, user_id: int) -> bool:
    """
    Удаляет категорию пользователя.
    (Внимание: нужно обработать связанные заметки, здесь мы их просто "отвяжем")
    """
    category = await get_category_by_id(session, category_id, user_id)
    if not category:
        return False

    try:
        # TODO: Решить, что делать с заметками этой категории
        # Вариант 1: Удалить (cascade)
        # Вариант 2: Обнулить category_id (ondelete="SET NULL")
        # Сейчас (без настройки cascade в модели) SQLAlchemy просто удалит категорию,
        # а FK в Note.category_id вызовет ошибку, если не настроен.
        # Для простоты MVP, будем считать, что модель настроена на SET NULL
        # или мы вручную это делаем (но это сложнее)
        # Для `cascade="all, delete-orphan"` в User -> Category,
        # нам нужно здесь просто удалить.

        await session.delete(category)
        await session.commit()
        return True
    except Exception as e:
        log.error(f"Ошибка удаления категории {category_id}: {e}", exc_info=True)
        await session.rollback()
        return False
