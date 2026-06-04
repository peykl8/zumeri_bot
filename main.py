import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN
from db import (
    init_db,
    save_group_topics,
    get_group_topics,
    update_empty_topic,
    save_broker,
    get_broker
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class BrokerRegister(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


def make_topic_name(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if len(lines) < 2:
        return None

    fio = lines[0].split()
    car = lines[1]

    if len(fio) < 3:
        return None

    surname = fio[0]
    name_initial = fio[1][0].upper()
    patronymic_initial = fio[2][0].upper()

    topic_name = f"{surname} {name_initial}. {patronymic_initial}. {car}"

    return topic_name[:128]


def make_contacts_text(broker) -> str:
    if not broker:
        manager_block = (
            "Менеджер не найден в базе.\n"
            "Попросите менеджера написать боту /register."
        )
    else:
        telegram_id, username, name, phone = broker
        username_text = f"@{username}" if username else "Telegram username не указан"

        manager_block = (
            f"{phone}\n"
            f"{username_text}\n"
            f"{name} - ваш менеджер, который непосредственно вами сейчас занимается."
        )

    return (
        "89957730239\n"
        "@kozlikbebe\n"
        "Ксения (Сиан) - собственник компании\n\n"
        "89958660586\n"
        "@AlekBrokrer\n"
        "Александра - руководитель по таможенному оформлению\n\n"
        f"{manager_block}\n\n"
        "С вами на связи компания Зумеры🩷"
    )


async def setup_group_topics(chat_id: int, added_by_user_id: int | None = None):
    existing = await get_group_topics(chat_id)

    if existing and existing[0] and existing[1]:
        return existing

    contacts_topic = await bot.create_forum_topic(
        chat_id=chat_id,
        name="Контакты"
    )

    empty_topic = await bot.create_forum_topic(
        chat_id=chat_id,
        name="Пустая заявка"
    )

    await save_group_topics(
        chat_id=chat_id,
        empty_thread_id=empty_topic.message_thread_id,
        contacts_thread_id=contacts_topic.message_thread_id,
        added_by_user_id=added_by_user_id
    )

    broker = await get_broker(added_by_user_id) if added_by_user_id else None

    await bot.send_message(
        chat_id=chat_id,
        message_thread_id=contacts_topic.message_thread_id,
        text=make_contacts_text(broker)
    )

    return (
        empty_topic.message_thread_id,
        contacts_topic.message_thread_id,
        added_by_user_id
    )


@dp.message(Command("start"))
async def start_handler(message: Message):
    if message.chat.type == "private":
        await message.answer(
            "Бот запущен и работает.\n\n"
            "Чтобы зарегистрироваться как менеджер, напишите /register."
        )
    else:
        await message.answer("Бот запущен и работает!")


@dp.message(Command("register"), F.chat.type == "private")
async def register_handler(message: Message, state: FSMContext):
    await state.set_state(BrokerRegister.waiting_for_name)
    await message.answer("Введите ваше имя:")


@dp.message(BrokerRegister.waiting_for_name, F.chat.type == "private")
async def register_name_handler(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введите имя ещё раз:")
        return

    await state.update_data(name=name)
    await state.set_state(BrokerRegister.waiting_for_phone)
    await message.answer("Введите ваш номер телефона:")


@dp.message(BrokerRegister.waiting_for_phone, F.chat.type == "private")
async def register_phone_handler(message: Message, state: FSMContext):
    phone = message.text.strip()

    cleaned_phone = (
        phone
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if not cleaned_phone.isdigit() or len(cleaned_phone) < 10:
        await message.answer("Номер телефона выглядит неверно. Введите номер ещё раз:")
        return

    data = await state.get_data()
    name = data["name"]

    username = message.from_user.username

    await save_broker(
        telegram_id=message.from_user.id,
        username=username,
        name=name,
        phone=phone
    )

    await state.clear()

    username_text = f"@{username}" if username else "username не указан"

    await message.answer(
        "Вы зарегистрированы как менеджер.\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Telegram: {username_text}"
    )


@dp.message(Command("setup"))
async def setup_handler(message: Message):
    try:
        await setup_group_topics(
            chat_id=message.chat.id,
            added_by_user_id=message.from_user.id
        )
        await message.answer("Готово. Созданы ветки: Контакты и Пустая заявка.")
    except Exception as e:
        await message.answer(
            "Не получилось создать ветки.\n\n"
            "Проверь:\n"
            "1. В группе включены темы/ветки.\n"
            "2. Бот является администратором.\n"
            "3. У бота есть право управления темами.\n\n"
            f"Ошибка: {e}"
        )


@dp.my_chat_member()
async def bot_added_to_group(event: ChatMemberUpdated):
    if event.chat.type not in ("group", "supergroup"):
        return

    new_status = event.new_chat_member.status

    if new_status not in ("member", "administrator"):
        return

    try:
        await setup_group_topics(
            chat_id=event.chat.id,
            added_by_user_id=event.from_user.id
        )

        await bot.send_message(
            chat_id=event.chat.id,
            text="Бот подключён. Созданы ветки: Контакты и Пустая заявка."
        )

    except Exception as e:
        await bot.send_message(
            chat_id=event.chat.id,
            text=(
                "Бот добавлен, но не смог создать ветки.\n\n"
                "Скорее всего, в группе не включены темы или у бота нет права управления темами.\n"
                "Включи темы вручную в настройках группы и выдай боту право управления темами.\n"
                "После этого напиши /setup.\n\n"
                f"Ошибка: {e}"
            )
        )


@dp.message()
async def handle_empty_topic_message(message: Message):
    if not message.message_thread_id:
        return

    if not message.text:
        return

    topics = await get_group_topics(message.chat.id)

    if not topics:
        return

    empty_thread_id, contacts_thread_id, added_by_user_id = topics

    if message.message_thread_id != empty_thread_id:
        return

    new_topic_name = make_topic_name(message.text)

    if not new_topic_name:
        await message.answer(
            "Неверный формат заявки.\n\n"
            "Нужно так:\n"
            "Фамилия Имя Отчество\n"
            "Марка Модель"
        )
        return

    try:
        await bot.edit_forum_topic(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            name=new_topic_name
        )

        await asyncio.sleep(3)

        new_empty_topic = await bot.create_forum_topic(
            chat_id=message.chat.id,
            name="Пустая заявка"
        )

        await update_empty_topic(
            chat_id=message.chat.id,
            empty_thread_id=new_empty_topic.message_thread_id
        )

    except Exception as e:
        await message.answer(f"Ошибка при обработке заявки: {e}")


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())