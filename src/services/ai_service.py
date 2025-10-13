import httpx
from src.core.config import settings
from src.models import Category
from typing import List, Optional
import logging
import json

log = logging.getLogger(__name__)

async def categorize_note_with_ollama(text: str, categories: List[Category]) -> Optional[int]:
    """
    Отправляет текст заметки и список категорий в Ollama
    для получения наиболее подходящей категории.
    Возвращает ID категории.
    """
    if not categories:
        log.warning("Нет категорий для классификации заметки.")
        return None

    # Формируем список имен категорий с описаниями
    category_list_str = "\n".join(
        f"- ID: {c.id}, Имя: {c.name}, Описание: {c.description or 'Нет'}"
        for c in categories
    )

    # Формируем промпт для Ollama
    system_prompt = f"""
Ты - ИИ-ассистент для финансового учета.
Твоя задача - проанализировать текст заметки о трате и выбрать ОДНУ наиболее подходящую категорию из предоставленного списка.
Ты ДОЛЖЕН ответить ТОЛЬКО ОДНИМ ЧИСЛОМ - ID категории.
Не пиши ничего, кроме ID.

Вот список доступных категорий (ID, Имя, Описание):
{category_list_str}

Если НИ ОДНА категория не подходит, ответь "0".
"""

    user_prompt = f"Текст заметки: \"{text}\""

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json" # Ollama 3.1+
        # Для старых версий Ollama, которые не поддерживают "format: json"
        # и "system", нужно объединить промпты и парсить ответ.
        # "prompt": f"{system_prompt}\n\n{user_prompt}"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_API_URL}/api/generate",
                json=payload
            )
            response.raise_for_status() # Вызовет ошибку, если статус 4xx/5xx

            response_data = response.json()

            # Парсим ответ
            raw_response = response_data.get("response", "").strip()

            # Если Ollama вернула JSON-строку (из-за "format": "json")
            # она может быть обернута в ```json ... ```
            if raw_response.startswith("```json"):
                raw_response = raw_response.strip("```json \n")

            log.info(f"Ollama raw response: {raw_response}")

            # Пытаемся извлечь ID
            try:
                # Ответ должен быть просто числом
                category_id = int(raw_response)
            except (ValueError, TypeError):
                # Если модель вернула JSON (например, {"id": 123})
                try:
                    parsed_json = json.loads(raw_response)
                    if isinstance(parsed_json, dict) and "id" in parsed_json:
                        category_id = int(parsed_json["id"])
                    elif isinstance(parsed_json, int):
                         category_id = parsed_json
                    else:
                        raise ValueError("Неожиданный формат JSON")
                except (json.JSONDecodeError, ValueError, TypeError):
                    log.warning(f"Ollama вернула невалидный ID: {raw_response}")
                    return None

            if category_id == 0:
                log.info("Ollama вернула ID=0 (нет подходящей категории).")
                return None

            # Проверяем, что такой ID есть в списке
            if category_id in [c.id for c in categories]:
                log.info(f"Ollama успешно категоризировала заметку. ID: {category_id}")
                return category_id
            else:
                log.warning(f"Ollama вернула ID, которого нет в списке: {category_id}")
                return None

    except httpx.ConnectError:
        log.error(f"Не удалось подключиться к Ollama по адресу: {settings.OLLAMA_API_URL}")
        return None
    except httpx.ReadTimeout:
        log.error(f"Ollama не ответила вовремя (timeout).")
        return None
    except httpx.HTTPStatusError as e:
        log.error(f"Ollama вернула ошибку: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        log.error(f"Неизвестная ошибка при запросе к Ollama: {e}", exc_info=True)
        return None
