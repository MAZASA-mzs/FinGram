import json
from src.infrastructure.database.models import User

def test_user_categories_exhaustive():
    """
    [Exhaustive Testing]
    Проверка всех возможных типов данных в списке категорий пользователя.
    """
    user = User()
    # Тестируем пустой список, очень длинные названия, спецсимволы, цифры
    cases = [
        [],
        ["A" * 100],
        ["!@#$%^&*()"],
        ["12345"],
        ["Категория с пробелом"]
    ]
    for case in cases:
        user.set_categories(case)
        assert user.get_categories() == case