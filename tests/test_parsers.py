import pytest
import pandas as pd
from src.infrastructure.implementations import SberParser


def test_validate_format_success():
    parser = SberParser()
    assert parser.validate_format("file.xlsx") is True
    assert parser.validate_format("file.xls") is True


def test_validate_format_failure():
    parser = SberParser()
    assert parser.validate_format("file.csv") is False
    assert parser.validate_format("file.txt") is False


def test_parse_valid_excel(tmp_path):
    # 1. Подготовка (Arrange)
    parser = SberParser()
    file_path = tmp_path / "statement.xlsx"

    # Создаем DataFrame, имитирующий выписку Сбера
    df = pd.DataFrame({
        'Дата': ['01.10.2023', '02.10.2023'],
        'Сумма': ['1000', '500,50'],
        'Описание операции': ['Перевод', 'Магазин']
    })
    df.to_excel(file_path, index=False)

    # 2. Действие (Act)
    transactions = parser.parse(str(file_path))

    # 3. Проверка (Assert)
    assert len(transactions) == 2
    assert transactions[1].amount == 500.50  # Проверка конвертации запятой
    assert transactions[1].description == "Магазин"


def test_parse_empty_or_broken(tmp_path):
    parser = SberParser()
    file_path = tmp_path / "broken.xlsx"

    # Файл без нужных колонок
    df = pd.DataFrame({'Col1': [1, 2], 'Col2': [3, 4]})
    df.to_excel(file_path, index=False)

    transactions = parser.parse(str(file_path))

    # Должен вернуть пустой список (так как нет колонок "Дата" и "Сумма")
    assert transactions == []