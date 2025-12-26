import pytest
import json
from unittest.mock import patch, AsyncMock
from src.infrastructure.llm.yandex import YandexGPTProvider
from src.core.dtypes import Transaction


@pytest.mark.asyncio
async def test_yandex_categorization():
    provider = YandexGPTProvider("api_key", "folder_id")

    # Имитация ответа от Yandex API
    mock_response_data = {
        "output": [{
            "content": [{
                "text": "```json\n{\"category\": \"Тест\", \"comment\": \"Ок\"}\n```"
            }]
        }]
    }

    # Патчим aiohttp.ClientSession.post
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Настраиваем контекстный менеджер ответа
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_response_data
        mock_post.return_value.__aenter__.return_value = mock_resp

        tx = Transaction(date=None, amount=100, description="Test")
        result = await provider.categorize_transaction(tx, [], ["Тест"], "")

        assert result['category'] == "Тест"
        assert result['comment'] == "Ок"