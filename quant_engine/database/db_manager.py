"""
==============================================================================
  QUANT ENGINE — DATABASE ORM & PERSISTENCE MANAGER
==============================================================================
"""

import os, sqlite3, json, datetime
from quant_engine.config.system_config import DATABASE_PATH

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Market Data Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                vwap REAL, funding_rate REAL, open_interest REAL,
                UNIQUE(timestamp, symbol)
            );
            """)

            # Discovered Patterns Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT UNIQUE,
                horizon TEXT,
                state_condition TEXT,
                sample_size INTEGER,
                win_rate REAL,
                expected_return REAL,
                sharpe REAL,
                oos_sharpe REAL,
                is_promoted INTEGER DEFAULT 0
            );
            """)

            # Model Versions & Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_version TEXT UNIQUE,
                architecture TEXT,
                train_period TEXT,
                val_accuracy REAL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT
            );
            """)

            # Trade Memory Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                fees REAL,
                slippage REAL,
                regime TEXT,
                pattern_id TEXT,
                model_version TEXT,
                explanation TEXT,
                mode TEXT
            );
            """)

            # Research Experiments Log Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT UNIQUE,
                hypothesis TEXT,
                features_used TEXT,
                oos_expectancy REAL,
                status TEXT,
                created_at TEXT
            );
            """)

            conn.commit()

    def log_trade(self, trade_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO trades 
            (trade_id, timestamp, symbol, side, entry_price, exit_price, pnl, pnl_pct, fees, slippage, regime, pattern_id, model_version, explanation, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get("trade_id"),
                trade_data.get("timestamp", datetime.datetime.now().isoformat()),
                trade_data.get("symbol"),
                trade_data.get("side", "BUY"),
                trade_data.get("entry_price", 0.0),
                trade_data.get("exit_price", 0.0),
                trade_data.get("pnl", 0.0),
                trade_data.get("pnl_pct", 0.0),
                trade_data.get("fees", 0.0),
                trade_data.get("slippage", 0.0),
                trade_data.get("regime", "BULL_LOW_VOL"),
                trade_data.get("pattern_id", "PATTERN-001"),
                trade_data.get("model_version", "v1.0"),
                trade_data.get("explanation", ""),
                trade_data.get("mode", "PAPER")
            ))
            conn.commit()
