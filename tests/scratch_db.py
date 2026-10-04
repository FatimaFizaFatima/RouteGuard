import asyncio
from app.db.db import init_db

async def main():
    db = await init_db("test_usage.db")
    cur = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(await cur.fetchall())
    await db.close()

asyncio.run(main())