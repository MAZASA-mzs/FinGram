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

    import re
    from datetime import datetime

    def _parse_date_robust(self, val) -> datetime:
        """Более надежный парсинг даты с поддержкой тире и различных форматов."""
        if isinstance(val, datetime):
            return val

        # Приводим к строке, чистим пробелы и приводим к нижнему регистру
        val_str = str(val).strip().lower()

        # Словарь месяцев (важно: 'мая' и 'май' обрабатываются корректно)
        months = {
            'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04', 'мая': '05', 'май': '05',
            'июн': '06', 'июл': '07', 'авг': '08', 'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12'
        }

        # Заменяем названия месяцев на числа
        for k, v in months.items():
            if k in val_str:
                # Заменяем месяц и пробуем нормализовать разделители
                val_str = val_str.replace(k, v)
                break

        # Оставляем цифры, пробелы, точки, двоеточия И тире
        val_str = re.sub(r'[^\d\s\.:-]', ' ', val_str)
        # Убираем двойные пробелы
        val_str = re.sub(r'\s+', ' ', val_str).strip()

        # Список форматов для проверки
        formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
            "%d %m %Y %H:%M",
            "%d %m %Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d-%m-%Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue

        # Fallback: ручной разбор, если стандартные форматы не подошли
        try:
            # Ищем все группы цифр в строке
            nums = re.findall(r'\d+', val_str)
            if len(nums) >= 3:
                # Если первая группа из 4 цифр — это год (ГГГГ ММ ДД)
                if len(nums[0]) == 4:
                    return datetime(int(nums[0]), int(nums[1]), int(nums[2]))
                # Иначе считаем, что год в конце (ДД ММ ГГГГ)
                elif len(nums[2]) == 4:
                    return datetime(int(nums[2]), int(nums[1]), int(nums[0]))
        except Exception:
            pass

        print(f"!!! Failed to parse date: {val}")
        return datetime.now()