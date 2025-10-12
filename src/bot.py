import logging
import io
import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.db import async_session_factory
from src.models import User, Note
from src.services import user_service, category_service, ai_service, parser_service, matching_service, report_service
from src.schemas import CategoryCreate

log = logging.getLogger(__name__)

# --- Инициализация бота ---
try:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
except Exception as e:
    log.critical(f"Ошибка инициализации Telegram-бота: {e}", exc_info=True)
    exit(1)


# --- FSM (Машина состояний) ---
class Form(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_desc = State()
    waiting_for_report_start_date = State()
    waiting_for_report_end_date = State()
    waiting_for_note_text = State() # Для команды /note

# --- Middleware (Аутентификация и Сессия) ---

class DbSessionMiddleware:
    """
    Middleware для внедрения сессии БД в каждый хэндлер.
    """
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)

class AuthMiddleware:
    """
    Middleware для проверки "белого списка" пользователей.
    """
    def __init__(self, admin_list: list[int]):
        self.admin_list = admin_list

    async def __call__(self, handler, event, data):
        # Проверяем, что event это Message или CallbackQuery
        if not hasattr(event, "from_user"):
             return await handler(event, data)

        user_id = event.from_user.id

        if not self.admin_list or user_id in self.admin_list:
            # Получаем или создаем пользователя в БД
            session: AsyncSession = data["session"]
            user_obj = await user_service.get_or_create_user(
                session,
                telegram_id=user_id,
                username=event.from_user.username
            )
            data["user"] = user_obj # Внедряем объект User
            return await handler(event, data)
        else:
            log.warning(f"Доступ запрещен для пользователя: {user_id}")
            if isinstance(event, Message):
                await event.answer("Доступ запрещен. Эта система предназначена для приватного использования.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен.", show_alert=True)
            return


# --- Хэндлеры (Обработчики команд) ---

@dp.message(CommandStart())
async def cmd_start(message: Message, user: User):
    """
    Обработчик команды /start
    """
    await message.answer(
        f"Привет, {user.username or 'пользователь'}!\n\n"
        "Я твой личный финансовый ассистент FinGram.\n"
        "Я помогу тебе учесть траты, которые банк не смог.\n\n"
        "<b>Как это работает:</b>\n"
        "1. Когда тратишь наличные или делаешь перевод, "
        "просто отправь мне заметку (например: 'Кофе и круассан в кафе 350р') или используй команду /note.\n"
        "2. Я (с помощью ИИ) постараюсь отнести ее к одной из твоих категорий.\n"
        "3. Позже, загрузи банковскую выписку (.xlsx) (команда /upload).\n"
        "4. Я автоматически сопоставлю твои заметки и транзакции из выписки.\n\n"
        "<b>Доступные команды:</b>\n"
        "/note - Создать заметку о трате\n"
        "/categories - Управление категориями\n"
        "/upload - Загрузить выписку (.xlsx)\n"
        "/report - Получить CSV-отчет\n"
        "/help - Эта справка"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    # /start содержит всю справку
    await cmd_start(message, data.get("user")) # user здесь может быть не в data, а в параметрах

# --- 1. User Flow: Создание заметки ---

@dp.message(Command("note"))
async def cmd_note(message: Message, state: FSMContext):
    """
    Начало FSM для создания заметки
    """
    await message.answer("Пожалуйста, введите текст вашей заметки о трате:")
    await state.set_state(Form.waiting_for_note_text)

@dp.message(Form.waiting_for_note_text)
async def process_note_text_fsm(message: Message, state: FSMContext, user: User, session: AsyncSession):
    """
    Получение текста заметки (через FSM)
    """
    await state.clear()
    await process_note_message(message, user, session)

@dp.message(F.text & ~F.text.startswith('/'))
async def process_note_message(message: Message, user: User, session: AsyncSession):
    """
    Обработка любого текстового сообщения как заметки
    """
    note_text = message.text
    if len(note_text) < 3:
        await message.answer("Слишком короткая заметка.")
        return

    await message.answer(f"Заметка принята: <i>«{note_text}»</i>\n\nИщу подходящую категорию...")

    # 1. Получаем категории пользователя
    categories = await category_service.get_user_categories(session, user_id=user.id)
    if not categories:
        await message.answer("У вас пока нет ни одной категории. ИИ не сможет классифицировать заметку.\n"
                             "Пожалуйста, создайте категории: /categories")
        category_id = None
    else:
        # 2. Отправляем в Ollama
        category_id = await ai_service.categorize_note_with_ollama(note_text, categories)

    # 3. Сохраняем заметку в БД
    new_note = Note(
        user_id=user.id,
        text=note_text,
        category_id=category_id,
        timestamp=message.date # Используем время сообщения из Telegram
    )
    session.add(new_note)
    await session.commit()

    if category_id:
        category = next((c.name for c in categories if c.id == category_id), "Неизвестная")
        await message.answer(f"✅ Заметка сохранена и отнесена к категории: <b>{category}</b>")
    else:
        await message.answer("✅ Заметка сохранена, но ИИ не смог подобрать категорию. "
                             "Она будет сопоставлена с транзакцией по времени.")

# --- 2. User Flow: Загрузка выписки (.xlsx) ---

@dp.message(Command("upload"))
async def cmd_upload(message: Message):
    await message.answer("Пожалуйста, прикрепите банковскую выписку в формате .xlsx")

@dp.message(F.document)
async def process_document(message: Message, user: User, session: AsyncSession):
    document = message.document
    if not document.file_name.endswith('.xlsx'):
        await message.answer("Это не .xlsx файл. Пожалуйста, загрузите корректную выписку.")
        return

    await message.answer(f"Файл <code>{document.file_name}</code> получен. Начинаю обработку...")

    try:
        # 1. Скачиваем файл
        file_info = await bot.get_file(document.file_id)
        file_content_stream = await bot.download_file(file_info.file_path)
        file_content = file_content_stream.read()

        # 2. Парсим
        # (Этот сервис может выкинуть ValueError)
        parsed_transactions = parser_service.parse_sberbank_xlsx(file_content, user_id=user.id)

        if not parsed_transactions:
            await message.answer("В файле не найдено транзакций расходов. Обработка завершена.")
            return

        # 3. Сохраняем транзакции в БД
        # TODO: Добавить проверку на дубликаты (по user_id, timestamp, amount, description)

        tx_objects = [Transaction(**data) for data in parsed_transactions]
        session.add_all(tx_objects)
        await session.commit()

        await message.answer(f"Успешно загружено <b>{len(tx_objects)}</b> транзакций.\n"
                             f"Запускаю автоматическое сопоставление с вашими заметками...")

        # 4. Запускаем сервис сопоставления
        match_count = await matching_service.find_and_match_transactions(session, user_id=user.id)

        await message.answer(f"✅ Готово! Автоматически сопоставлено: <b>{match_count}</b> пар (заметка + транзакция).")

    except ValueError as e:
        log.warning(f"Ошибка парсинга XLSX от {user.id}: {e}")
        await message.answer(f"<b>Ошибка обработки файла:</b>\n{e}")
    except Exception as e:
        log.error(f"Критическая ошибка обработки файла {user.id}: {e}", exc_info=True)
        await message.answer("Произошла внутренняя ошибка. Не удалось обработать файл.")


# --- 3. User Flow: Управление категориями ---

@dp.message(Command("categories"))
async def cmd_categories(message: Message, user: User, session: AsyncSession):
    """
    Показывает список категорий и кнопки управления
    """
    categories = await category_service.get_user_categories(session, user_id=user.id)

    builder = InlineKeyboardBuilder()
    if categories:
        text = "<b>Ваши категории:</b>\n"
        for i, cat in enumerate(categories):
            text += f"{i+1}. <b>{cat.name}</b>\n    <i>{cat.description or '...'}</i>\n"
            # TODO: Добавить кнопки для редактирования/удаления
            # builder.button(text=f"Удалить {cat.name}", callback_data=f"cat_delete_{cat.id}")
    else:
        text = "У вас пока нет категорий."

    builder.button(text="➕ Добавить категорию", callback_data="cat_add")
    builder.adjust(1) # Все кнопки в один столбец

    await message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "cat_add")
async def cb_cat_add(callback: CallbackQuery, state: FSMContext):
    """
    Начало FSM для добавления категории
    """
    await callback.message.answer("Введите название для новой категории:")
    await state.set_state(Form.waiting_for_category_name)
    await callback.answer()

@dp.message(Form.waiting_for_category_name)
async def process_cat_name(message: Message, state: FSMContext):
    """
    Получили имя, запрашиваем описание
    """
    await state.update_data(cat_name=message.text)
    await message.answer("Отлично. Теперь введите краткое описание (или 'пропустить'):")
    await state.set_state(Form.waiting_for_category_desc)

@dp.message(Form.waiting_for_category_desc)
async def process_cat_desc(message: Message, state: FSMContext, user: User, session: AsyncSession):
    """
    Получили описание, создаем категорию
    """
    data = await state.get_data()
    cat_name = data.get("cat_name")
    cat_desc = message.text if message.text.lower() not in ['пропустить', 'skip'] else None

    await state.clear()

    category_in = CategoryCreate(name=cat_name, description=cat_desc)
    category = await category_service.create_user_category(session, user_id=user.id, category_data=category_in)

    if category:
        await message.answer(f"✅ Категория <b>«{category.name}»</b> создана.")
    else:
        await message.answer(f"⚠️ Категория <b>«{cat_name}»</b> уже существует.")

    # Показываем обновленный список
    await cmd_categories(message, user, session)

# --- 4. User Flow: Получение отчета ---

@dp.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext):
    """
    Начало FSM для отчета. Запрашивает дату начала.
    """
    # TODO: Сделать Inline-календарь
    today = datetime.date.today()
    first_day_of_month = today.replace(day=1)

    await message.answer(
        "За какой период вы хотите получить отчет?\n"
        f"Введите <b>дату начала</b> (например, {first_day_of_month.strftime('%Y-%m-%d')}):"
    )
    await state.set_state(Form.waiting_for_report_start_date)

@dp.message(Form.waiting_for_report_start_date)
async def process_report_start_date(message: Message, state: FSMContext):
    """
    Получили дату начала, запрашиваем дату конца.
    """
    try:
        start_date = datetime.datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(start_date=start_date)

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        await message.answer(f"Отлично. Теперь введите <b>дату окончания</b> (например, {today_str}):")
        await state.set_state(Form.waiting_for_report_end_date)

    except ValueError:
        await message.answer("Неверный формат. Введите дату как ГГГГ-ММ-ДД:")

@dp.message(Form.waiting_for_report_end_date)
async def process_report_end_date(message: Message, state: FSMContext, user: User, session: AsyncSession):
    """
    Получили дату конца, генерируем отчет.
    """
    try:
        end_date = datetime.datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        start_date = data.get("start_date")
        await state.clear()

        if start_date > end_date:
            await message.answer("Дата начала не может быть позже даты окончания. Попробуйте /report заново.")
            return

        await message.answer("Готовлю отчет, это может занять минуту...")

        # Генерируем CSV
        csv_data_bytes = await report_service.generate_csv_report(
            session,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date
        )

        if not csv_data_bytes:
            await message.answer("За указанный период не найдено транзакций.")
            return

        # Отправляем файл
        report_filename = f"report_{user.id}_{start_date}_to_{end_date}.csv"
        file_to_send = BufferedInputFile(csv_data_bytes, filename=report_filename)

        await message.answer_document(
            file_to_send,
            caption=f"Ваш отчет по расходам c {start_date} по {end_date}"
        )

    except ValueError:
        await message.answer("Неверный формат. Введите дату как ГГГГ-ММ-ДД:")
    except Exception as e:
        await state.clear()
        log.error(f"Ошибка генерации отчета для {user.id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при создании отчета.")


# --- Функции запуска/остановки ---

async def on_startup():
    """
    Выполняется при старте бота.
    """
    # Настраиваем команды в меню Telegram
    commands = [
        types.BotCommand(command="start", description="Перезапуск/Справка"),
        types.BotCommand(command="note", description="Создать заметку о трате"),
        types.BotCommand(command="categories", description="Управление категориями"),
        types.BotCommand(command="upload", description="Загрузить выписку (.xlsx)"),
        types.BotCommand(command="report", description="Получить отчет (.csv)"),
    ]
    await bot.set_my_commands(commands)
    log.info("Бот запущен и команды установлены.")


async def on_shutdown():
    """
    Выполняется при остановке бота.
    """
    log.info("Бот останавливается...")
    await bot.session.close()


# --- Регистрация Middleware ---
dp.update.middleware(DbSessionMiddleware(session_pool=async_session_factory))
dp.message.middleware(AuthMiddleware(admin_list=settings.ADMIN_LIST))
dp.callback_query.middleware(AuthMiddleware(admin_list=settings.ADMIN_LIST))
