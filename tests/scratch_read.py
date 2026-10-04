import sqlite3

con = sqlite3.connect("usage.db")
rows = con.execute(
    "SELECT id, task_type, model_used, attempts, status, error_type, latency_ms "
    "FROM requests ORDER BY id DESC LIMIT 10"
)
for row in rows:
    print(row)