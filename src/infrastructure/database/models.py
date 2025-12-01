from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, BigInteger
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)

    # Пользовательские настройки (храним как JSON строку или отдельные поля)
    categories_list = Column(Text, default="Еда, Транспорт, Жилье, Развлечения, Здоровье")
    custom_prompts = Column(Text, default="Если я пишу 'Вкусвилл', это категория Еда.")

    created_at = Column(DateTime, default=datetime.utcnow)

    notes = relationship("Note", back_populates="user")


class Note(Base):
    """
    Заметки на естественном языке, которые пользователь отправляет боту.
    """
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))

    raw_text = Column(Text, nullable=False)  # Исходный текст
    created_at = Column(DateTime, default=datetime.utcnow)  # Время создания заметки

    # Флаг, была ли заметка использована для закрытия какой-то транзакции
    # (для сложной логики можно расширить до Many-to-Many)
    is_processed = Column(Boolean, default=False)

    user = relationship("User", back_populates="notes")

# Транзакции здесь не храним персистентно, так как они парсятся из файла "на лету",
# но если нужно вести историю, можно добавить модель Transaction.