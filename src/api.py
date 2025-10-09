from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from src.core.db import get_db_session
from src.services import category_service
from src.schemas import CategoryCreate, CategoryRead, CategoryUpdate, MessageResponse
from src.models import User # Нужен для аутентификации

# Временная "аутентификация" для API
# TODO: Заменить на JWT или другую схему
from fastapi import Header

log = logging.getLogger(__name__)

app = FastAPI(
    title="FinGram API",
    description="API для управления категориями и настройками",
    version="0.1.0"
)

# --- Временная "аутентификация" ---
# В идеале, бот должен присылать TG_USER_ID, а API его проверять
# Для простоты MVP, мы будем передавать ID в заголовке
# ВНИМАНИЕ: Это НЕБЕЗОПАСНО для продакшена.
async def get_current_user_id(x_user_id: int = Header(None)) -> int:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходим заголовок X-User-Id"
        )
    # Здесь можно добавить проверку, есть ли такой user в БД
    return x_user_id
# -----------------------------------


@app.get("/health", response_model=MessageResponse, tags=["System"])
async def health_check():
    """
    Проверка работоспособности API.
    """
    return {"message": "API is running"}


@app.post("/api/v1/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED, tags=["Categories"])
async def create_category(
    category_in: CategoryCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Создает новую категорию для пользователя.
    """
    log.info(f"API: Создание категории '{category_in.name}' для {user_id}")
    category = await category_service.create_user_category(db, user_id, category_in)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Категория с таким именем уже существует"
        )
    return category


@app.get("/api/v1/categories", response_model=List[CategoryRead], tags=["Categories"])
async def get_categories(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Возвращает список всех категорий пользователя.
    """
    categories = await category_service.get_user_categories(db, user_id)
    return categories


@app.put("/api/v1/categories/{category_id}", response_model=CategoryRead, tags=["Categories"])
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Обновляет существующую категорию.
    """
    category = await category_service.update_user_category(db, category_id, user_id, category_in)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена или принадлежит другому пользователю"
        )
    return category


@app.delete("/api/v1/categories/{category_id}", response_model=MessageResponse, tags=["Categories"])
async def delete_category(
    category_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Удаляет категорию.
    """
    success = await category_service.delete_user_category(db, category_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена или ошибка при удалении"
        )
    return {"message": "Категория успешно удалена"}
