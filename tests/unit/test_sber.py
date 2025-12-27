from datetime import datetime

from src.infrastructure.parsers.sber import SberParser


def test_tc_u01_parse_complex_dates(create_dummy_excel):
    """TC-U01: Парсинг дат разных формата."""
    parser = SberParser()

    # Подготовка данных с разными форматами
    raw_data = {
        "Дата": ["01-01-2024", "31 дек 2023"],
        "Сумма в валюте операции": [100.0, 200.0],
        "Описание": ["Test1", "Test2"],
        "Валюта": ["RUB", "RUB"]
    }
    file_path = create_dummy_excel("dates.xlsx", raw_data)

    transactions = parser.parse(file_path)

    assert len(transactions) == 2
    assert transactions[0].date == datetime(2024, 1, 1, 0, 0)
    assert transactions[1].date == datetime(2023, 12, 31, 0, 0)


def test_tc_u04_zero_amounts(create_dummy_excel):
    """TC-U04: Обработка нулевых сумм."""
    parser = SberParser()

    # Подготовка данных с нулевой суммой
    raw_data = {
        "Дата": ["01.01.2024"],
        "Сумма в валюте операции": [0.0],
        "Описание": ["Zero transaction"],
        "Валюта": ["RUB"]
    }
    file_path = create_dummy_excel("zeros.xlsx", raw_data)

    transactions = parser.parse(file_path)

    # Ожидаем, что нулевая транзакция парсится корректно как 0
    assert len(transactions) == 1
    assert transactions[0].amount == 0.0