import json
import re
import aiohttp
from typing import List
from src.core.dtypes import Transaction, UserNote
from src.core.interfaces import BaseLLMProvider


class YandexGPTProvider(BaseLLMProvider):
    def __init__(self, api_key: str, folder_id: str, model_name: str = "yandexgpt-lite"):
        self.api_key = api_key
        self.folder_id = folder_id
        # Правильный путь для Assistant API согласно документации
        self.url = "https://rest-assistant.api.cloud.yandex.net/v1/responses"
        self.model_uri = f"gpt://{folder_id}/{model_name}"

    def _clean_json_response(self, response_text: str) -> str:
        clean_text = re.sub(r'```json\s*', '', response_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'```', '', clean_text)
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

        notes_context = "\n".join([f"- {n.text}" for n in nearby_notes]) if nearby_notes else "Нет заметок."

        # Формируем промпт
        prompt = f"""ЗАДАЧА: Определи категорию траты.
Транзакция: "{transaction.description}", Сумма: {transaction.amount}
Заметки: {notes_context}
КАТЕГОРИИ: {json.dumps(categories, ensure_ascii=False)}
Глобальные подсказки: {user_hints}
Верни ТОЛЬКО валидный JSON в формате:
{{"category": "название_категории", "comment": "почему выбрана"}}"""

        # Структура payload должна соответствовать методу responses.create
        payload = {
            "model": self.model_uri,
            "input": prompt,  # В Assistant API используется 'input', а не 'messages'
            "completionConfig": {
                "temperature": 0.1,
                "maxTokens": 1500
            }
        }

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Доступ к тексту через output[0].content[0].text
                        try:
                            raw_response = data['output'][0]['content'][0]['text']
                            clean_json_str = self._clean_json_response(raw_response)
                            result = json.loads(clean_json_str)

                            if result.get('category') not in categories:
                                result['category'] = 'Разное'
                            return result
                        except (KeyError, IndexError, json.JSONDecodeError):
                            return {"category": "Разное", "comment": "Ошибка обработки формата Yandex"}
                    else:
                        # Если снова будет ошибка, мы увидим её статус в поле комментария
                        return {"category": "Разное", "comment": f"Yandex API Error {resp.status}"}
            except Exception as e:
                return {"category": "Разное", "comment": f"Connection Error: {str(e)}"}