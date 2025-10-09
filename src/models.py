import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.core.db import Base


class User(Base):
    """
    Модель пользователя.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    # Связи
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    """
    Модель категории расходов, созданной пользователем.
    """
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)

    # Связи
    user = relationship("User", back_populates="categories")
    notes = relationship("Note", back_populates="category")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='_user_category_name_uc'),
    )


class Note(Base):
    """
    Модель заметки (описания траты), оставленной пользователем.
    """
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.UTC), index=True)

    # Связь с категорией (может быть null, если ИИ не смог)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Связь с транзакцией (когда произойдет сопоставление)
    matched_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, unique=True)

    # Связи
    user = relationship("User", back_populates="notes")
    category = relationship("Category", back_populates="notes")
    matched_transaction = relationship("Transaction", back_populates="matched_note", foreign_keys=[matched_transaction_id])


class Transaction(Base):
    """
    Модель транзакции из банковской выписки.
    """
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)

    # Связь с заметкой (когда произойдет сопоставление)
    matched_note_id = Column(Integer, ForeignKey("notes.id"), nullable=True, unique=True)

    # Связи
    user = relationship("User", back_populates="transactions")
    matched_note = relationship("Note", back_populates="matched_transaction", foreign_keys=[matched_note_id])
