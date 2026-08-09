import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "antigravity.db"
)

def get_connection():
    return sqlite3.connect(DB_PATH)

# -----------------------------------
# CAPITAL
# -----------------------------------

def get_latest_portfolio():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT capital
        FROM portfolio
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return 100000

# -----------------------------------
# TOTAL TRADES
# -----------------------------------

def get_total_trades():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM trades
    """)

    count = cursor.fetchone()[0]

    conn.close()

    return count

# -----------------------------------
# WIN RATE
# -----------------------------------

def get_win_rate():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM trades
    """)

    total = cursor.fetchone()[0]

    if total == 0:
        conn.close()
        return 0

    cursor.execute("""
        SELECT COUNT(*)
        FROM trades
        WHERE profit > 0
    """)

    wins = cursor.fetchone()[0]

    conn.close()

    return round(
        wins / total * 100,
        2
    )

# -----------------------------------
# TOTAL PROFIT
# -----------------------------------

def get_total_profit():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(profit)
        FROM trades
    """)

    result = cursor.fetchone()[0]

    conn.close()

    if result is None:
        return 0

    return round(result, 2)