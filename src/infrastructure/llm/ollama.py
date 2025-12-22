import json
from typing import List

import aiohttp

from src.core.dtypes import Transaction, UserNote
from src.core.interfaces import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def categorize_transaction(
            self,
            transaction: Transaction,
            nearby_notes: List[UserNote],
            categories: List[str],
            user_hints: str
    ) -> dict:

        notes_text = "\n".join([f"- [{n.timestamp.strftime('%d.%m %H:%M')}] {n.text}" for n in nearby_notes])
        if not notes_text:
            notes_text = "Нет заметок рядом с этой датой."

        prompt = f"""
        Роль: Финансовый аналитик.
        Задача: Категоризировать транзакцию, используя описание от банка и заметки пользователя.

        ВХОДНЫЕ ДАННЫЕ:
        1. Транзакция: {transaction.date.strftime('%Y-%m-%d')} | {transaction.amount} RUB | {transaction.description}
        2. Доступные категории: {", ".join(categories)}
        3. Заметки пользователя (могут пояснять трату):
        {notes_text}
        4. Глобальные подсказки пользователя: {user_hints}

        ПРАВИЛА:
        - Если есть подходящая заметка по сумме/времени, бери информацию из неё.
        - Если заметки нет, анализируй описание банка.
        - Ответ должен быть валидным JSON.

        ФОРМАТ ОТВЕТА (JSON):
        {{
            "category": "одна из доступных категорий или 'Разное'",
            "comment": "короткое пояснение или текст из заметки"
        }}
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return json.loads(data.get('response', '{}'))
            except Exception as e:
                print(f"LLM Error: {e}")

        return {"category": "Ошибка API", "comment": "Не удалось связаться с LLM"}
