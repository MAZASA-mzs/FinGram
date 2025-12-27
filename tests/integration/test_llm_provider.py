import pytest
from unittest.mock import patch, AsyncMock

from src.core.dtypes import Transaction
from src.infrastructure.llm.yandex import YandexGPTProvider


@pytest.mark.asyncio
async def test_tc_u02_clean_json_markdown():
    """TC-U02: Очистка JSON-ответа от Markdown блоков."""
    provider = YandexGPTProvider("key", "folder")

    # Подготовка данных в формате
    # data['output'][0]['content'][0]['text']
    raw_llm_response = {
        "output": [
            {
                "content": [
                    {
                        "text": "```json\n{\"category\": \"Еда\", \"comment\": \"Ок\"}\n```"
                    }
                ]
            }
        ]
    }

    # Патчим aiohttp
    # Тот самый "серый ящик" (прим. уставшего кодера)
    with patch("src.infrastructure.llm.yandex.aiohttp.ClientSession.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = raw_llm_response
        mock_post.return_value.__aenter__.return_value = mock_resp

        tx = Transaction(date=None, amount=100.0, description="Burger King")

        # Передаем список категорий, включающий 'Еда'
        result = await provider.categorize_transaction(
            transaction=tx,
            nearby_notes=[],
            categories=["Еда", "Транспорт"],
            user_hints=""
        )

        # Теперь проверка пройдет успешно
        assert isinstance(result, dict)
        assert result['category'] == "Еда"
        assert result['comment'] == "Ок"


@pytest.mark.asyncio
async def test_yandex_api_error_handling():
    """Дополнительный тест: обработка ошибки 500 от API."""
    # Да, было настолько мало тестов, что чисто для объёма я решил написать ещё один
    # Больше тестов богу тестов!
    provider = YandexGPTProvider("key", "folder")

    with patch("src.infrastructure.llm.yandex.aiohttp.ClientSession.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_post.return_value.__aenter__.return_value = mock_resp

        tx = Transaction(date=None, amount=100.0, description="Test")
        result = await provider.categorize_transaction(tx, [], ["Еда"], "")

        assert result['category'] == "Разное"
        assert "Error 500" in result['comment']