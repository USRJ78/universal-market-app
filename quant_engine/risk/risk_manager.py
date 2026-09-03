"""
==============================================================================
  QUANT ENGINE — DETERMINISTIC RISK ENGINE & HARD LIMITS
==============================================================================
  IMPORTANT: The Machine Learning model NEVER has unrestricted authority.
  All trades MUST pass through deterministic risk controls before execution.
==============================================================================
"""

from quant_engine.config.system_config import (
    MAX_POSITION_SIZE_PCT,
    MAX_DAILY_LOSS_PCT,
    MAX_TOTAL_EXPOSURE_PCT,
    STOP_LOSS_DEFAULT_PCT
)

class RiskEngine:
    def __init__(self):
        self.max_pos_pct   = MAX_POSITION_SIZE_PCT
        self.max_daily_loss = MAX_DAILY_LOSS_PCT
        self.max_exposure   = MAX_TOTAL_EXPOSURE_PCT

    def validate_trade(self, portfolio_state: dict, proposed_trade: dict) -> dict:
        """Deterministically validates position sizing and risk bounds prior to order execution"""
        total_equity = portfolio_state.get("total_equity", 100000.0)
        current_daily_pnl_pct = portfolio_state.get("daily_pnl_pct", 0.0)

        # 1. Daily Loss Limit Check
        if current_daily_pnl_pct <= -self.max_daily_loss:
            return {
                "approved": False,
                "reason": f"HARD RISK BREACH: Daily loss threshold (-{self.max_daily_loss*100:.1f}%) exceeded!",
                "position_size": 0.0
            }

        # 2. Maximum Position Size Calculation
        proposed_alloc = proposed_trade.get("allocation_pct", 0.15)
        safe_alloc_pct = min(proposed_alloc, self.max_pos_pct)
        position_size  = total_equity * safe_alloc_pct

        # 3. Stop-Loss Enforcement
        stop_loss_price = proposed_trade.get("entry_price", 100.0) * (1.0 - STOP_LOSS_DEFAULT_PCT)

        return {
            "approved": True,
            "reason": "APPROVED BY RISK ENGINE",
            "position_size": position_size,
            "allocation_pct": safe_alloc_pct,
            "stop_loss_price": stop_loss_price,
            "max_loss_amount": position_size * STOP_LOSS_DEFAULT_PCT
        }
