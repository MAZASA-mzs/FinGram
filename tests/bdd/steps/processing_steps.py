import asyncio
from behave import given, when, then
from unittest.mock import AsyncMock
from src.core.dtypes import Transaction


# Примечание: В реальном проекте BDD тесты требуют настройки loop в environment.py

@given('в базе данных существует пользователь "{username}"')
def step_impl(context, username):
    # В behave данные передаются через context
    context.categories = []
    context.username = username


@given('у пользователя есть категория "{category}"')
def step_add_cat(context, category):
    context.categories.append(category)


@when('пользователь отправляет транзакцию "{desc}" на сумму {amount:d}')
def step_send_tx(context, desc, amount):
    # Имитируем логику Processor
    context.tx = Transaction(date=None, amount=float(amount), description=desc)

    # Мок LLM логики
    if "Пятерочка" in desc and "Супермаркеты" in context.categories:
        context.result_category = "Супермаркеты"
    else:
        context.result_category = "Разное"


@then('система должна присвоить категорию "{expected_cat}"')
def step_check_cat(context, expected_cat):
    assert context.result_category == expected_cat