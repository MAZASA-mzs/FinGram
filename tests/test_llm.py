import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from src.infrastructure.llm.ollama import OllamaProvider


@pytest.fixture
def ollama_provider():
    return OllamaProvider("http://localhost:11434", "llama3")


@pytest.mark.asyncio
async def test_llm_resilience_to_malformed_json(ollama_provider, sample_transaction):
    """
    [Error Guessing]
    Модель возвращает текст вместо JSON.
    Ожидание: Фолбэк к 'Разное' с комментарием об ошибке чтения.
    """
    # Создаем мок ответа aiohttp
    mock_resp = AsyncMock()
    mock_resp.status = 200
    # Имитируем, что Ollama вернула невалидный JSON в поле response
    mock_resp.json.return_value = {"response": "Я думаю, это категория Еда, но я не JSON"}

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_resp

        result = await ollama_provider.categorize_transaction(
            transaction=sample_transaction,
            nearby_notes=[],
            categories=["Еда"],
            user_hints=""
        )

        assert result["category"] == "Разное"
        assert "Ошибка чтения ответа" in result["comment"]


@pytest.mark.asyncio
async def test_llm_connection_error_handling(ollama_provider, sample_transaction):
    """
    [Cause-Effect]
    Причина: Исключение при попытке запроса (сервер выключен).
    Следствие: Возврат 'Разное' и комментарий 'Ошибка соединения'.
    """
    with patch("aiohttp.ClientSession.post", side_effect=Exception("Connection refused")):
        result = await ollama_provider.categorize_transaction(
            sample_transaction, [], ["Еда"], ""
        )
        assert result["category"] == "Разное"
        assert "Ошибка соединения" in result["comment"]


@pytest.mark.asyncio
async def test_llm_success_path(ollama_provider, sample_transaction):
    """[Happy Path] Корректный разбор JSON."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {
        "response": json.dumps({"category": "Еда", "comment": "Из заметки"})
    }

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_resp

        result = await ollama_provider.categorize_transaction(
            sample_transaction, [], ["Еда"], ""
        )
        assert result["category"] == "Еда"
        assert result["comment"] == "Из заметки"