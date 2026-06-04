import aiosqlite

DB_NAME = "database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_topics (
                chat_id INTEGER PRIMARY KEY,
                empty_thread_id INTEGER,
                contacts_thread_id INTEGER,
                added_by_user_id INTEGER
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS brokers (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL
            )
        """)

        await db.commit()


async def save_group_topics(
    chat_id: int,
    empty_thread_id: int,
    contacts_thread_id: int,
    added_by_user_id: int | None = None
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO group_topics (
                chat_id,
                empty_thread_id,
                contacts_thread_id,
                added_by_user_id
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                empty_thread_id = excluded.empty_thread_id,
                contacts_thread_id = excluded.contacts_thread_id,
                added_by_user_id = excluded.added_by_user_id
        """, (
            chat_id,
            empty_thread_id,
            contacts_thread_id,
            added_by_user_id
        ))
        await db.commit()


async def get_group_topics(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT empty_thread_id, contacts_thread_id, added_by_user_id
            FROM group_topics
            WHERE chat_id = ?
        """, (chat_id,))
        return await cursor.fetchone()


async def update_empty_topic(chat_id: int, empty_thread_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO group_topics (chat_id, empty_thread_id)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                empty_thread_id = excluded.empty_thread_id
        """, (chat_id, empty_thread_id))
        await db.commit()


async def save_broker(
    telegram_id: int,
    username: str | None,
    name: str,
    phone: str
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO brokers (telegram_id, username, name, phone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                name = excluded.name,
                phone = excluded.phone
        """, (
            telegram_id,
            username,
            name,
            phone
        ))
        await db.commit()


async def get_broker(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT telegram_id, username, name, phone
            FROM brokers
            WHERE telegram_id = ?
        """, (telegram_id,))
        return await cursor.fetchone()


async def get_all_brokers():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT telegram_id, username, name, phone
            FROM brokers
            ORDER BY name
        """)
        return await cursor.fetchall()