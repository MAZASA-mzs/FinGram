from pydantic import BaseModel, ConfigDict
from typing import Optional

# --- Категории ---

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: Optional[str] = None # Позволяем частичное обновление

class CategoryRead(CategoryBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True) # orm_mode = True

# --- Ответы API ---

class MessageResponse(BaseModel):
    message: str
