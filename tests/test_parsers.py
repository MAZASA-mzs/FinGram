import pytest
from unittest.mock import patch, MagicMock
from src.infrastructure.parsers.sber import SberParser
from src.core.dtypes import Transaction


class TestSberParser:
    def test_sber_parser_format_validation(self):
        parser = SberParser()
        assert parser.validate_format("report.xlsx") is True
        assert parser.validate_format("data.csv") is False

    @patch("pandas.read_excel")
    def test_parser_successful_data_extraction(self, mock_read):
        """Проверка логики поиска заголовков и создания Transaction."""
        # 1. Мокаем первый вызов read_excel (поиск заголовка)
        mock_df_header = MagicMock()
        mock_df_header.iterrows.return_value = [(0, MagicMock(astype=lambda x: MagicMock(
            str=MagicMock(lower=lambda: MagicMock(tolist=lambda: ['дата', 'сумма', 'описание'])))))]

        # 2. Мокаем второй вызов (чтение данных)
        mock_df_data = MagicMock()
        mock_df_data.columns = ['дата операции', 'сумма', 'описание операции']
        mock_df_data.iterrows.return_value = [(0, {
            'дата операции': '15.10.2023',
            'сумма': '1500,50',
            'описание операции': 'Магнит'
        })]

        mock_read.side_effect = [mock_df_header, mock_df_data]

        parser = SberParser()
        transactions = parser.parse("dummy.xlsx")

        assert len(transactions) == 1
        assert isinstance(transactions[0], Transaction)
        assert transactions[0].amount == 1500.50
        assert transactions[0].description == "Магнит"