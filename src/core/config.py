import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
log = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Класс для загрузки и хранения настроек приложения из .env файла.
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    TELEGRAM_BOT_TOKEN: str
    ADMIN_USER_IDS: str
    OLLAMA_API_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    DATABASE_URL: str = "sqlite+aiosqlite:///./fingram.db"

    @property
    def ADMIN_LIST(self) -> list[int]:
        """
        Преобразует строку ADMIN_USER_IDS в список integer ID.
        """
        if not self.ADMIN_USER_IDS:
            log.warning("ADMIN_USER_IDS не задан. Бот будет доступен всем.")
            return []
        try:
            return [int(uid.strip()) for uid in self.ADMIN_USER_IDS.split(',') if uid.strip()]
        except ValueError as e:
            log.error(f"Ошибка парсинга ADMIN_USER_IDS: {e}")
            return []


@lru_cache
def get_settings() -> Settings:
    """
    Фабричная функция для получения синглтона настроек.
    """
    return Settings()

# Экземпляр настроек, который будет использоваться во всем приложении
settings = get_settings()
