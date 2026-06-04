import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated

from config import BOT_TOKEN
from db import init_db, save_group_topics, get_group_topics, update_empty_topic

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


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


async def setup_group_topics(chat_id: int):
    existing = await get_group_topics(chat_id)

    if existing and existing[0] and existing[1]:
        return

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
        contacts_thread_id=contacts_topic.message_thread_id
    )


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Бот запущен и работает!")


@dp.message(Command("setup"))
async def setup_handler(message: Message):
    try:
        await setup_group_topics(message.chat.id)
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
        await setup_group_topics(event.chat.id)

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

    empty_thread_id, contacts_thread_id = topics

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