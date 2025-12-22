import pandas as pd
import aiohttp
import json
import io
import csv
from datetime import datetime
from typing import List

from src.core.interfaces import BaseBankParser, BaseLLMProvider, BaseReportGenerator
from src.core.dtypes import Transaction, UserNote


# --- PARSER ---
class SberParser(BaseBankParser):
    def validate_format(self, file_path: str) -> bool:
        """Проверка по расширению файла[cite: 44]."""
        return file_path.endswith('.xlsx') or file_path.endswith('.xls')

    def parse(self, file_path: str) -> List[Transaction]:
        """
        Парсинг выписки Сбербанка на основе структуры:
        [Номер, Дата, Тип опера, Категория, Сумма, Валюта, Сумма в р, Описание, Состояние].
        """
        # Читаем файл целиком без заголовков для поиска начала таблицы [cite: 58]
        df_raw = pd.read_excel(file_path, header=None)

        start_row = 0
        # Ищем строку, содержащую ключевые заголовки со скриншота
        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if any('дата' in s for s in row_str) and any('сумма' in s for s in row_str):
                start_row = i
                break

        # Перечитываем файл с правильным заголовком [cite: 66]
        df = pd.read_excel(file_path, header=start_row)

        # Очистка названий колонок от лишних пробелов и переносов
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]

        transactions = []
        for _, row in df.iterrows():
            try:
                # Маппинг полей согласно скриншоту
                # Используем .get() и проверку подстрок для гибкости
                date_val = self._find_col(row, 'Дата')
                amount_val = self._find_col(row, 'Сумма в р') or self._find_col(row, 'Сумма')
                desc_val = self._find_col(row, 'Описание')

                if pd.isna(date_val) or pd.isna(amount_val):
                    continue

                # Обработка даты (в Сбере может быть строкой '01 дек. 2024')
                dt = self._parse_date(date_val)

                # Очистка суммы (удаление пробелов и замена запятой)
                clean_amount = float(str(amount_val).replace('\xa0', '').replace(' ', '').replace(',', '.'))

                transactions.append(Transaction(
                    date=dt,
                    amount=clean_amount,
                    description=str(desc_val) if not pd.isna(desc_val) else "Без описания"
                ))
            except Exception as e:
                # Пропускаем строки с итогами или ошибками [cite: 85]
                continue

        return transactions

    def _find_col(self, row, name_part):
        """Вспомогательный метод для поиска значения в колонке по части названия."""
        for col_name in row.index:
            if name_part.lower() in col_name.lower():
                return row[col_name]
        return None

    def _parse_date(self, val):
        """Конвертация даты из различных форматов Сбера[cite: 77]."""
        if isinstance(val, datetime):
            return val

        val_str = str(val).strip()
        # Попытка распарсить стандартный формат DD.MM.YYYY
        try:
            return datetime.strptime(val_str, "%d.%m.%Y")
        except:
            pass

        # Попытка распарсить текстовый формат '01 дек. 2024' (упрощенно)
        months = {
            'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04', 'мая': '05', 'июн': '06',
            'июл': '07', 'авг': '08', 'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12'
        }
        try:
            parts = val_str.split()
            day = parts[0].zfill(2)
            month = months.get(parts[1].lower().replace('.', ''), '01')
            year = parts[2]
            return datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y")
        except:
            return datetime.now()  # Fallback

# --- LLM ---
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
            "format": "json"
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


# --- REPORT GENERATOR ---
class CSVReportGenerator(BaseReportGenerator):
    def generate(self, transactions: List[Transaction]) -> io.BytesIO:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Дата', 'Сумма', 'Валюта', 'Описание', 'Категория', 'Комментарий'])

        for tx in transactions:
            writer.writerow([
                tx.date.strftime("%Y-%m-%d"),
                tx.amount,
                tx.currency,
                tx.description,
                tx.category,
                tx.comment
            ])

        output.seek(0)
        # Конвертируем в BytesIO для отправки телеграмом
        return io.BytesIO(output.getvalue().encode('utf-8'))