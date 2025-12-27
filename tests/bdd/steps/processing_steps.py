from behave import given, when, then

from src.core.dtypes import Transaction


# Эмуляция бизнес-логики (упрощенная модель того, что делает LLM+Processor)
def mock_business_logic(transaction, categories):
    desc = transaction.description.lower()
    if "пятерочка" in desc and "Супермаркеты" in categories:
        return "Супермаркеты"
    if "аптека" in desc and "Здоровье" in categories:
        return "Здоровье"
    return "Разное"

@given('у пользователя настроены категории "{cat_string}"')
def step_set_categories(context, cat_string):
    context.categories = [c.strip() for c in cat_string.split(',')]

@when('поступает транзакция "{desc}" на сумму {amount:d}')
def step_receive_tx(context, desc, amount):
    context.tx = Transaction(date=None, amount=float(amount), description=desc)
    # Вызываем "ядро" системы
    context.result_category = mock_business_logic(context.tx, context.categories)

@then('система должна присвоить категорию "{expected_cat}"')
def step_check_category(context, expected_cat):
    assert context.result_category == expected_cat, \
        f"Ожидалось {expected_cat}, получено {context.result_category}"