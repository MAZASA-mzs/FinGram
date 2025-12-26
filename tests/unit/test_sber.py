import pytest
from datetime import datetime
from src.infrastructure.parsers.sber import SberParser


def test_validate_format():
    parser = SberParser()
    assert parser.validate_format("file.xlsx") is True
    assert parser.validate_format("file.xls") is True
    assert parser.validate_format("file.csv") is False


def test_parse_transactions(create_dummy_excel):
    file_path = create_dummy_excel("sber_test.xlsx")
    parser = SberParser()

    transactions = parser.parse(file_path)

    assert len(transactions) == 2
    assert transactions[0].amount == 500.0
    assert transactions[0].description == "Покупка в магазине"
    assert isinstance(transactions[0].date, datetime)
    # Проверка "пропуска" строк
    assert transactions[0].currency == "RUB"