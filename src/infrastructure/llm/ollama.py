import json
import re
from typing import List
import aiohttp
from src.core.dtypes import Transaction, UserNote
from src.core.interfaces import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def _clean_json_response(self, response_text: str) -> str:
        """Очищает ответ LLM от Markdown и лишнего текста, оставляя только JSON."""
        # Убираем блоки кода ```json ... ```
        clean_text = re.sub(r'```json\s*', '', response_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'```', '', clean_text)

        # Пытаемся найти границы JSON объекта { ... }
        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}')

        if start_idx != -1 and end_idx != -1:
            clean_text = clean_text[start_idx:end_idx + 1]

        return clean_text.strip()

    async def categorize_transaction(
            self,
            transaction: Transaction,
            nearby_notes: List[UserNote],
            categories: List[str],
            user_hints: str
    ) -> dict:

        # Формируем контекст заметок. Для глупой модели важно не перегружать контекст.
        if nearby_notes:
            notes_context = "\n".join([f"- {n.text} ({n.timestamp.strftime('%d.%m')})" for n in nearby_notes])
        else:
            notes_context = "Нет заметок."

        # Максимально "сухой" промпт
        prompt = f"""
ЗАДАЧА: Определи категорию траты и напиши короткий комментарий.

ВХОДНЫЕ ДАННЫЕ:
Транзакция: "{transaction.description}"
Сумма: {transaction.amount}
Дата: {transaction.date.strftime('%Y-%m-%d')}
Заметки пользователя (могут содержать подсказку):
{notes_context}

СПИСОК КАТЕГОРИЙ (ВЫБЕРИ ОДНУ СТРОГО ИЗ СПИСКА):
{json.dumps(categories, ensure_ascii=False)}

Глобальные подсказки: {user_hints}

ИНСТРУКЦИЯ:
1. Если в заметках есть совпадение по сумме или смыслу — используй информацию оттуда.
2. Если заметок нет — угадай категорию по описанию транзакции.
3. Верни ТОЛЬКО валидный JSON.

ПРИМЕР ОТВЕТА:
{{
  "category": "Еда",
  "comment": "Покупка в магазине (из заметки)"
}}
"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # Ollama поддерживает enforced JSON mode
            "options": {
                "temperature": 0.1,  # Снижаем креативность для стабильности
                "num_ctx": 4096
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_response = data.get('response', '{}')

                        # Пытаемся почистить и распарсить
                        clean_json_str = self._clean_json_response(raw_response)
                        try:
                            result = json.loads(clean_json_str)
                            # Проверяем, что категория реально из списка, иначе "Разное"
                            if result.get('category') not in categories:
                                result['category'] = 'Разное'
                            return result
                        except json.JSONDecodeError:
                            print(f"JSON Parse Error. Raw: {raw_response}")
                            return {"category": "Разное", "comment": "Ошибка чтения ответа LLM"}
                    else:
                        print(f"Ollama Error {resp.status}")
            except Exception as e:
                print(f"Connection Error: {e}")

        return {"category": "Разное", "comment": "Ошибка соединения"}