import sqlite3
import os

db_path = os.path.join(
    os.path.dirname(__file__),
    "antigravity.db"
)

conn = sqlite3.connect(db_path)

cursor = conn.cursor()

cursor.execute("""
INSERT INTO portfolio
(
    date,
    capital
)
VALUES
(
    date('now'),
    180000
)
""")

conn.commit()

conn.close()

print("Test Portfolio Added")