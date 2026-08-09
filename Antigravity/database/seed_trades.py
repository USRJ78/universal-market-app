import sqlite3
import os
import random

db_path = os.path.join(
    os.path.dirname(__file__),
    "antigravity.db"
)

conn = sqlite3.connect(db_path)

cursor = conn.cursor()

for i in range(50):

    profit = random.randint(
        -3000,
        8000
    )

    cursor.execute("""
        INSERT INTO trades
        (
            symbol,
            entry_price,
            exit_price,
            profit,
            strategy
        )
        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?
        )
    """,
    (
        "RELIANCE",
        1000,
        1100,
        profit,
        "UTBOT"
    ))

conn.commit()

conn.close()

print("Trades Added")