import csv
import io
from typing import List

from src.core.dtypes import Transaction, ExportFile
from src.core.interfaces import BaseReportGenerator


class BasicCSVReportGenerator(BaseReportGenerator):
    def generate(self, transactions: List[Transaction]) -> ExportFile:
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
        return ExportFile(
            'csv',
            io.BytesIO(output.getvalue().encode('utf-8'))
        )
