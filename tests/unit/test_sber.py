import pytest
import pandas as pd
from datetime import datetime
from src.infrastructure.parsers.sber import SberParser


class TestSberParser:
    @pytest.fixture
    def parser(self):
        return SberParser()

    @pytest.mark.parametrize("date_input, expected_date", [
        ("01.01.2024", datetime(2024, 1, 1)),
        ("01.01.2024 15:30", datetime(2024, 1, 1, 15, 30)),
        ("1 янв 2024", datetime(2024, 1, 1)),
        ("10 фев 2024", datetime(2024, 2, 10)),
        ("2024-03-01", datetime(2024, 3, 1)),
        # Проверка fallback логики (ДД ММ ГГГГ через пробел)
        ("15 05 2024", datetime(2024, 5, 15)),
        # Проверка передачи объекта datetime напрямую
        (datetime(2023, 12, 31), datetime(2023, 12, 31)),
    ])
    def test_date_parsing_robustness(self, parser, date_input, expected_date):
        """TC-U01: Проверка устойчивости парсинга дат в различных форматах."""
        assert parser._parse_date_robust(date_input) == expected_date

    def test_header_search_and_column_normalization(self, tmp_path, parser):
        """TC-P02: Проверка поиска заголовка в глубине файла и нормализации имен колонок."""
        file_path = tmp_path / "sber_format.xlsx"

        # Эмулируем структуру Сбера: мусор сверху, потом заголовок
        data = [
            ["Выписка по счету", None, None],
            ["Клиент: Иван Иванов", None, None],
            [None, None, None],
            ["Дата", "Сумма в рублях", "Описание операции"],  # Заголовок
            ["01.01.2024", "100.00", "Покупка 1"]
        ]
        pd.DataFrame(data).to_excel(file_path, index=False, header=False)

        transactions = parser.parse(str(file_path))

        assert len(transactions) == 1
        assert transactions[0].amount == 100.0
        assert transactions[0].description == "Покупка 1"

    def test_amount_cleaning_complex(self, tmp_path, parser):
        """TC-P03: Очистка сумм с пробелами, запятыми и спецсимволами."""
        file_path = tmp_path / "dirty_amounts.xlsx"
        data = {
            "Дата": ["01.01.2024", "02.01.2024"],
            "Сумма": ["1\xa0500,75", "- 2 000.50"],  # Неразрывные пробелы и разные разделители
            "Описание": ["Desc 1", "Desc 2"]
        }
        pd.DataFrame(data).to_excel(file_path, index=False)

        transactions = parser.parse(str(file_path))

        assert transactions[0].amount == 1500.75
        assert transactions[1].amount == -2000.50

    def test_alternative_column_names(self, tmp_path, parser):
        """TC-P04: Проверка поиска альтернативных названий колонок (Сумма в валюте операции)."""
        file_path = tmp_path / "alt_cols.xlsx"
        data = {
            "Дата операции": ["01.01.2024"],
            "Сумма в валюте операции": ["500.00"],
            "Детализация": ["Кофе"]
        }
        pd.DataFrame(data).to_excel(file_path, index=False)

        transactions = parser.parse(str(file_path))

        assert len(transactions) == 1
        assert transactions[0].amount == 500.0
        # Описание не найдено (в коде ищется 'описание'), должен быть fallback
        assert transactions[0].description == "Без описания"

    def test_missing_required_data(self, tmp_path, parser):
        """TC-P05: Обработка пустых строк и отсутствующих обязательных колонок."""
        file_path = tmp_path / "empty_rows.xlsx"
        data = {
            "Дата": ["01.01.2024", None, "03.01.2024"],
            "Сумма": ["100", "200", None],
            "Описание": ["A", "B", "C"]
        }
        pd.DataFrame(data).to_excel(file_path, index=False)

        transactions = parser.parse(str(file_path))

        # Должна остаться только первая строка, так как в других NaN в дате или сумме
        assert len(transactions) == 1
        assert transactions[0].date.day == 1

    def test_validate_format(self, parser):
        """TC-P06: Проверка валидации расширений."""
        assert parser.validate_format("report.xlsx") is True
        assert parser.validate_format("report.xls") is True
        assert parser.validate_format("report.pdf") is False
        assert parser.validate_format("report.csv") is False