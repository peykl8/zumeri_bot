import aiosqlite

DB_NAME = "database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_topics (
                chat_id INTEGER PRIMARY KEY,
                empty_thread_id INTEGER,
                contacts_thread_id INTEGER
            )
        """)
        await db.commit()


async def save_group_topics(chat_id: int, empty_thread_id: int, contacts_thread_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO group_topics (chat_id, empty_thread_id, contacts_thread_id)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                empty_thread_id = excluded.empty_thread_id,
                contacts_thread_id = excluded.contacts_thread_id
        """, (chat_id, empty_thread_id, contacts_thread_id))
        await db.commit()


async def get_group_topics(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT empty_thread_id, contacts_thread_id
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