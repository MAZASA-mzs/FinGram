import datetime

from src.core.dtypes import Transaction
from src.infrastructure.reporters.basic_csv import BasicCSVReportGenerator


def test_tc_u03_csv_generation():
    """TC-U03: Валидация структуры CSV отчета."""
    generator = BasicCSVReportGenerator()
    transactions = [
        Transaction(date=datetime.datetime(2025, 12, 12, 0, 0),
                    amount=100.0,
                    description="Test",
                    category="Еда")
    ]

    csv_result = generator.generate(transactions)
    csv_result = csv_result.file_content.read().decode("utf-8")


    assert "Дата,Сумма,Валюта,Описание,Категория,Комментарий" in csv_result
    assert "100.0" in csv_result
    assert "Еда" in csv_result
    # Ну и чисто ради прикола
    expected_csv = "Дата,Сумма,Валюта,Описание,Категория,Комментарий\r\n" \
                   "2025-12-12,100.0,RUB,Test,Еда,\r\n"
    assert csv_result == expected_csv
