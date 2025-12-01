import pandas as pd
import aiohttp
import json
from datetime import datetime
from typing import List
from src.core.interfaces import BaseBankParser, BaseLLMProvider, Transaction, UserNote


# --- PARSER IMPLEMENTATION ---

class SberParser(BaseBankParser):
    def validate_format(self, file_path: str) -> bool:
        # Упрощенная проверка расширения, в реальности можно проверить заголовки колонок
        return file_path.endswith('.xlsx') or file_path.endswith('.xls')

    def parse(self, file_path: str) -> List[Transaction]:
        # Примерная логика парсинга выписки Сбера (структура может меняться)
        # Обычно заголовки начинаются не с 1 строки.
        df = pd.read_excel(file_path, header=None)

        # Поиск строки с заголовками (обычно содержит "Дата", "Сумма")
        start_row = 0
        for i, row in df.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if 'дата' in row_str and 'сумма' in row_str:
                start_row = i
                break

        df = pd.read_excel(file_path, header=start_row)
        transactions = []

        for _, row in df.iterrows():
            try:
                # В реальности названия колонок нужно вынести в конфиг маппинга
                date_val = row.get('Дата операции') or row.get('Дата')
                amount_val = row.get('Сумма') or row.get('Сумма в валюте операции')
                desc_val = row.get('Описание операции') or row.get('Название')

                if pd.isna(date_val) or pd.isna(amount_val):
                    continue

                # Конвертация даты
                if isinstance(date_val, str):
                    dt = datetime.strptime(date_val, "%d.%m.%Y")  # формат сбера
                else:
                    dt = date_val

                transactions.append(Transaction(
                    date=dt,
                    amount=float(str(amount_val).replace(' ', '').replace(',', '.')),
                    description=str(desc_val)
                ))
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue

        return transactions


# --- LLM IMPLEMENTATION ---

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

        # Формируем промпт
        notes_text = "\n".join([f"- [{n.timestamp.strftime('%Y-%m-%d %H:%M')}] {n.text}" for n in nearby_notes])
        categories_text = ", ".join(categories)

        prompt = f"""
        Ты финансовый ассистент. Твоя задача - категоризировать банковскую транзакцию, используя заметки пользователя.

        Транзакция:
        Дата: {transaction.date}
        Сумма: {transaction.amount}
        Описание банка: {transaction.description}

        Заметки пользователя (вокруг даты транзакции):
        {notes_text}

        Доступные категории: {categories_text}

        Подсказки пользователя: {user_hints}

        ИНСТРУКЦИЯ:
        1. Найди заметку, которая по смыслу, сумме (может быть приблизительно) или времени подходит к транзакции.
        2. Учти, что одна заметка "Купил продукты и пиво" может относиться к двум транзакциям, или одна транзакция могла быть разбита.
        3. Если подходящей заметки нет, используй описание банка для догадки.
        4. Если совсем непонятно, категория "Разное".

        Верни ответ ТОЛЬКО в формате JSON:
        {{
            "category": "Название категории",
            "comment": "Пояснение, почему выбрана категория, или текст из заметки"
        }}
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response_text = data.get('response', '{}')
                        return json.loads(response_text)
                    else:
                        print(f"LLM Error: {resp.status}")
                        return {"category": "Ошибка LLM", "comment": "Сбой сети"}
            except Exception as e:
                print(f"Exception LLM: {e}")
                return {"category": "Ошибка", "comment": str(e)}