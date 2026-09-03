"""
==============================================================================
  QUANT ENGINE — SYSTEM CONFIGURATION MANAGER
==============================================================================
"""

import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Execution Mode: "PAPER" (Default) or "LIVE"
EXECUTION_MODE = os.getenv("QUANT_EXECUTION_MODE", "PAPER").upper()

# Database Connection
DATABASE_PATH = os.getenv("QUANT_DATABASE_PATH", os.path.join(BASE_DIR, "database", "quant_research.db"))

# Risk Engine Limits (Hard-Capped)
MAX_POSITION_SIZE_PCT = 0.35      # Max 35% of capital per position
MAX_DAILY_LOSS_PCT    = 0.05      # Max 5% portfolio daily loss threshold
MAX_TOTAL_EXPOSURE_PCT = 1.00     # Max 100% total portfolio exposure
MAX_LEVERAGE           = 3.0       # Max 3.0x leverage cap
STOP_LOSS_DEFAULT_PCT  = 0.015    # Default 1.5% stop loss

# API Credentials (Loaded securely from Environment)
GROWW_API_KEY      = os.getenv("GROWW_API_KEY", "")
DELTA_API_KEY      = os.getenv("DELTA_API_KEY", "t3tgPkmiiTDz11HNvFd3tj16xRhU7x")
DELTA_API_SECRET   = os.getenv("DELTA_API_SECRET", "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn")
DELTA_BASE_URL     = os.getenv("DELTA_BASE_URL", "https://cdn-ind.testnet.deltaex.org")
