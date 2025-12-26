from src.infrastructure.database.models import User


def test_user_categories():
    user = User()
    cats = ["Продукты", "Авто"]

    # Проверка сеттера
    user.set_categories(cats)
    assert '"Продукты"' in user._categories_json

    # Проверка геттера
    loaded_cats = user.get_categories()
    assert loaded_cats == cats
    assert isinstance(loaded_cats, list)


def test_empty_categories():
    user = User()
    assert user.get_categories() == []