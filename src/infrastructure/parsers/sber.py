from datetime import datetime
from typing import List

import pandas as pd

from src.core.dtypes import Transaction
from src.core.interfaces import BaseBankParser


class SberParser(BaseBankParser):
    def validate_format(self, file_path: str) -> bool:
        """Проверка по расширению файла."""
        return file_path.endswith('.xlsx') or file_path.endswith('.xls')

    def parse(self, file_path: str) -> List[Transaction]:
        """
        Парсинг выписки Сбербанка на основе структуры:
        [Номер, Дата, Тип опера, Категория, Сумма, Валюта, Сумма в р, Описание, Состояние].
        """
        # Читаем файл целиком без заголовков для поиска начала таблицы
        df_raw = pd.read_excel(file_path, header=None)

        start_row = 0
        # Ищем строку, содержащую ключевые заголовки со скриншота
        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if any('дата' in s for s in row_str) and any('сумма' in s for s in row_str):
                start_row = i
                break

        # Перечитываем файл с правильным заголовком
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
                # Пропускаем строки с итогами или ошибками
                continue

        return transactions

    def _find_col(self, row, name_part):
        """Вспомогательный метод для поиска значения в колонке по части названия."""
        for col_name in row.index:
            if name_part.lower() in col_name.lower():
                return row[col_name]
        return None

    def _parse_date(self, val):
        """Конвертация даты из различных форматов Сбера, включая '20 дек. 2025, 18:08'."""
        if isinstance(val, datetime):
            return val

        val_str = str(val).strip()

        # Попытка распарсить полные форматы с датой и временем/без:
        for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%d %m %Y %H:%M", "%d %m %Y"):
            try:
                return datetime.strptime(val_str, fmt)
            except Exception:
                pass

        # Мапа месяцев (короткие формы с/без точки)
        months = {
            'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04', 'май': '05', 'мая': '05',
            'июн': '06', 'июл': '07', 'авг': '08', 'сен': '09', 'сент': '09', 'окт': '10',
            'ноя': '11', 'дек': '12'
        }

        try:
            # Очищаем запятые и лишние пробелы
            s = val_str.replace(',', ' ').replace('.', ' . ').replace('  ', ' ').strip()
            parts = s.split()

            # Ожидаемые варианты:
            # ['20', 'дек', '.', '2025', '18:08'] -> 20 дек. 2025 18:08
            # ['20', 'дек', '.', '2025']          -> 20 дек. 2025
            # ['20', 'дек', '2025', '18:08']      -> 20 дек 2025 18:08
            # ['20', 'дек', '2025']               -> 20 дек 2025

            # Извлечь день
            day = parts[0].zfill(2)

            # Найти токен с названием месяца (следующий не-числовой токен)
            month_token = None
            year_token = None
            time_token = None
            for token in parts[1:]:
                tok = token.strip()
                if tok == '.':
                    continue
                if tok.replace(':', '').isdigit():
                    # это либо год (2025) либо время (18:08)
                    if ':' in tok:
                        time_token = tok
                    elif len(tok) == 4:
                        year_token = tok
                else:
                    # считаем это месяцем (например 'дек' или 'дек.')
                    month_token = tok.lower().replace('.', '')

            month = months.get(month_token, None)
            if month is None:
                # если не удалось сопоставить, попробуем второй элемент как месяц без очистки
                candidate = parts[1].lower().replace('.', '')
                month = months.get(candidate, '01')

            # если год не найден в токенах, возможно он находится сразу после месяца
            if not year_token:
                for token in parts[1:]:
                    if token.isdigit() and len(token) == 4:
                        year_token = token
                        break

            year = year_token or str(datetime.now().year)

            # Собираем строку для парсинга
            if time_token:
                parse_str = f"{day}.{month}.{year} {time_token}"
                return datetime.strptime(parse_str, "%d.%m.%Y %H:%M")
            else:
                parse_str = f"{day}.{month}.{year}"
                return datetime.strptime(parse_str, "%d.%m.%Y")

        except Exception as err:
            print(f"!!! Sber parser error: {err}")
            return datetime.now()  # Fallback
