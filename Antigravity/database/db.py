import sqlite3
import os

# --------------------------------------------------
# DATABASE LOCATION
# --------------------------------------------------

db_path = os.path.join(
    os.path.dirname(__file__),
    "antigravity.db"
)

print("\nDatabase Path:")
print(db_path)

# --------------------------------------------------
# CONNECT
# --------------------------------------------------

conn = sqlite3.connect(db_path)

cursor = conn.cursor()

# --------------------------------------------------
# TRADES TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS trades (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    symbol TEXT,

    entry_date TEXT,

    exit_date TEXT,

    entry_price REAL,

    exit_price REAL,

    quantity REAL,

    profit REAL,

    strategy TEXT
)
""")

# --------------------------------------------------
# PORTFOLIO TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS portfolio (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    date TEXT,

    capital REAL
)
""")

# --------------------------------------------------
# STRATEGIES TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS strategies (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    strategy_name TEXT,

    win_rate REAL,

    sharpe REAL,

    final_capital REAL
)
""")

# --------------------------------------------------
# BACKTEST TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS trades (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    symbol TEXT,

    entry_date TEXT,

    exit_date TEXT,

    entry_price REAL,

    exit_price REAL,

    quantity REAL,

    profit REAL,

    strategy TEXT
)
""")

# --------------------------------------------------
# SAVE
# --------------------------------------------------

conn.commit()

conn.close()

# --------------------------------------------------
# VERIFY
# --------------------------------------------------

print("\nDatabase Created Successfully")

print(
    "\nDatabase Exists:",
    os.path.exists(db_path)
)