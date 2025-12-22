from datetime import datetime
from typing import List
import pandas as pd
import re

from src.core.dtypes import Transaction
from src.core.interfaces import BaseBankParser


class SberParser(BaseBankParser):
    def validate_format(self, file_path: str) -> bool:
        return file_path.endswith('.xlsx') or file_path.endswith('.xls')

    def parse(self, file_path: str) -> List[Transaction]:
        # Читаем "сырой" файл
        df_raw = pd.read_excel(file_path, header=None)
        start_row = 0

        # Ищем заголовок
        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if any('дата' in s for s in row_str) and \
                    (any('сумма' in s for s in row_str) or any('сумма в валюте операции' in s for s in row_str)):
                start_row = i
                break

        # Перечитываем с заголовком
        df = pd.read_excel(file_path, header=start_row)
        # Нормализация имен колонок: нижний регистр, убрать переносы
        df.columns = [str(c).strip().replace('\n', ' ').lower() for c in df.columns]

        transactions = []
        for _, row in df.iterrows():
            try:
                # Поиск колонок по ключевым словам
                col_date = next((c for c in df.columns if 'дата' in c), None)
                col_amount = next((c for c in df.columns if 'сумма в руб' in c), None)
                if not col_amount:
                    col_amount = next((c for c in df.columns if 'сумма' in c), None)
                col_desc = next((c for c in df.columns if 'описание' in c), None)

                if not col_date or not col_amount:
                    continue

                date_val = row[col_date]
                amount_val = row[col_amount]
                desc_val = row[col_desc] if col_desc else "Без описания"

                if pd.isna(date_val) or pd.isna(amount_val):
                    continue

                dt = self._parse_date_robust(date_val)

                # Очистка суммы
                amount_str = str(amount_val).replace('\xa0', '').replace(' ', '').replace(',', '.')
                # Если сумма отрицательная (расход), делаем модуль, или оставляем как есть в зависимости от логики
                # Обычно парсеры хранят абсолютное значение + флаг расхода, но тут упростим:
                clean_amount = float(amount_str)

                transactions.append(Transaction(
                    date=dt,
                    amount=clean_amount,
                    currency="RUB",  # Явно задаем валюту
                    description=str(desc_val).strip(),
                    category="",  # Заполнит LLM
                    comment=""
                ))
            except Exception as e:
                # Логируем ошибку парсинга конкретной строки, но не падаем
                print(f"Skipping row error: {e}")
                continue

        return transactions

    def _parse_date_robust(self, val) -> datetime:
        """Более надежный парсинг даты."""
        if isinstance(val, datetime):
            return val

        val_str = str(val).strip().lower()

        # Словарь замен
        months = {
            'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04', 'май': '05', 'мая': '05',
            'июн': '06', 'июл': '07', 'авг': '08', 'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12'
        }

        # Заменяем буквенные месяцы на цифры
        for k, v in months.items():
            if k in val_str:
                val_str = val_str.replace(k, v).replace('.', ' ')
                break

        # Убираем все лишнее, оставляем цифры, точки, пробелы, двоеточия
        val_str = re.sub(r'[^\d\s\.:]', '', val_str)
        val_str = re.sub(r'\s+', ' ', val_str).strip()

        formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%d %m %Y %H:%M",
            "%d %m %Y",
            "%Y-%m-%d"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue

        # Fallback: пробуем распарсить просто как день.месяц.год, если год в конце
        try:
            parts = val_str.split()
            if len(parts) >= 3:
                # Предполагаем формат ДД ММ ГГГГ
                day, month, year = parts[0], parts[1], parts[2]
                if len(year) == 4:
                    return datetime(int(year), int(month), int(day))
        except:
            pass

        print(f"!!! Failed to parse date: {val}")
        return datetime.now()