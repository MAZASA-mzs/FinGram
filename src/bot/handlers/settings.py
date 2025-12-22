from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class SettingsStates(StatesGroup):
    waiting_categories = State()
    waiting_hints = State()


@router.message(Command("settings"))
async def cmd_settings(message: types.Message, user):
    cats = ", ".join(user.get_categories())
    hints = user.custom_prompts

    text = (
        f"⚙️ **Настройки**\n\n"
        f"📂 **Текущие категории:**\n{cats}\n\n"
        f"💡 **Твои подсказки для ИИ:**\n{hints}\n\n"
        f"Для изменения отправь:\n"
        f"/set\_cats <список через запятую>\n"
        f"/set\_hints <текст подсказки>"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("set_cats"))
async def set_categories(message: types.Message, user, db_session):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.answer("⚠️ Напиши список категорий через запятую после команды.")
        return

    raw_cats = args[1]
    new_cats = [c.strip() for c in raw_cats.split(',') if c.strip()]

    user.set_categories(new_cats)
    await db_session.commit()
    await message.answer("✅ Категории обновлены!")


@router.message(Command("set_hints"))
async def set_hints(message: types.Message, user, db_session):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.answer("⚠️ Напиши текст подсказки после команды.")
        return

    user.custom_prompts = args[1]
    await db_session.commit()
    await message.answer("✅ Подсказки обновлены!")