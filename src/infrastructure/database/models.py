import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)

    # Храним категории как JSON-строку
    _categories_json = Column("categories", Text, default="[]")

    # Пользовательские подсказки для LLM
    custom_prompts = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    notes = relationship("Note", back_populates="user")

    def get_categories(self) -> list[str]:
        if not self._categories_json:
            return []
        return json.loads(self._categories_json)

    def set_categories(self, categories: list[str]):
        self._categories_json = json.dumps(categories, ensure_ascii=False)


class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notes")