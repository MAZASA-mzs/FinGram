import pytest
import json
from aioresponses import aioresponses
from src.infrastructure.llm.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_llm_categorize_success(sample_transaction):
    # Arrange
    provider = OllamaProvider(base_url="http://test-ollama", model="llama2")
    expected_response = {
        "category": "Еда",
        "comment": "Покупка в магазине"
    }

    # Мокаем ответ от сервера Ollama
    # Ollama обычно возвращает JSON внутри поля 'response'
    ollama_api_response = {
        "response": json.dumps(expected_response)
    }

    with aioresponses() as m:
        m.post("http://test-ollama/api/generate", payload=ollama_api_response, status=200)

        # Act
        result = await provider.categorize_transaction(
            transaction=sample_transaction,
            nearby_notes=[],
            categories=["Еда", "Авто"],
            user_hints=""
        )

    # Assert
    assert result['category'] == "Еда"
    assert result['comment'] == "Покупка в магазине"


@pytest.mark.asyncio
async def test_llm_network_error(sample_transaction):
    # Arrange
    provider = OllamaProvider(base_url="http://test-ollama", model="llama2")

    with aioresponses() as m:
        # Имитируем ошибку 500
        m.post("http://test-ollama/api/generate", status=500)

        # Act
        result = await provider.categorize_transaction(
            transaction=sample_transaction,
            nearby_notes=[],
            categories=[],
            user_hints=""
        )

    # Assert - проверяем fallback (защитную) логику
    assert result['category'] == "Ошибка LLM"