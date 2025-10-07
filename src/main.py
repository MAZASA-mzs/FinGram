import asyncio
import uvicorn
import logging
from contextlib import asynccontextmanager

from src.api import app as fastapi_app
from src.bot import dp, bot, on_startup as bot_startup, on_shutdown as bot_shutdown
from src.core.db import init_db
from src.core.config import log # Используем настроенный логгер

@asynccontextmanager
async def lifespan(app):
    """
    Контекстный менеджер Lifespan для FastAPI.
    Выполняется при старте и остановке API.
    """
    log.info("FastAPI приложение запускается...")
    # 1. Инициализируем БД (создаем таблицы)
    await init_db()
    
    # 2. Настраиваем бота (устанавливаем команды)
    await bot_startup()
    
    # 3. Запускаем polling бота в фоновой задаче
    # bot.delete_webhook() # Убедимся, что webhook отключен
    bot_task = asyncio.create_task(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))
    
    log.info("Бот запущен в режиме polling.")
    
    yield # API готово к приему запросов
    
    # --- Код ниже выполнится при остановке API ---
    log.info("FastAPI приложение останавливается...")
    
    # 1. Останавливаем бота
    log.info("Остановка бота...")
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        log.info("Задача бота отменена.")
    await bot_shutdown()
    
    log.info("Приложение остановлено.")


# Применяем lifespan к FastAPI
fastapi_app.router.lifespan_context = lifespan


# Точка входа для Uvicorn (если запускать через `uvicorn src.main:fastapi_app`)
app = fastapi_app


# Точка входа для запуска через `python -m src.main`
if __name__ == "__main__":
    log.info("Запуск приложения через Uvicorn...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True, # Включите для разработки
        log_level="info"
    )
