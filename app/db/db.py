import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id     TEXT,
    ts             TEXT NOT NULL,
    task_type      TEXT,
    model_used     TEXT,
    attempts       TEXT,
    input_tokens   INTEGER DEFAULT 0,
    output_tokens  INTEGER DEFAULT 0,
    cost           REAL DEFAULT 0,
    latency_ms     REAL,
    status         TEXT NOT NULL,
    error_type     TEXT
);
"""

INDEX = "CREATE INDEX IF NOT EXISTS idx_requests_ts ON requests(ts);"


async def init_db(path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(path)
    await db.execute(SCHEMA)
    await db.execute(INDEX)
    await db.commit()
    return db