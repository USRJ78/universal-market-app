"""
==============================================================================
  QUANT ENGINE — PORTFOLIO MANAGER & PERFORMANCE TRACKER
==============================================================================
"""

import numpy as np

class PortfolioManager:
    def __init__(self, initial_capital=100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.equity_curve = [initial_capital]
        self.trades = []

    def get_state(self) -> dict:
        """Calculates portfolio metrics: Equity, PnL, Sharpe, Max Drawdown"""
        current_equity = self.equity_curve[-1]
        pnl = current_equity - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100.0

        eq_arr = np.array(self.equity_curve)
        peaks  = np.maximum.accumulate(eq_arr)
        dds    = (eq_arr - peaks) / (peaks + 1e-9)
        mdd    = float(np.min(dds)) * 100.0 if len(dds) > 0 else 0.0

        return {
            "total_equity": round(current_equity, 2),
            "cash": round(self.cash, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "max_drawdown_pct": round(mdd, 2),
            "total_trades_count": len(self.trades)
        }

    def record_trade_exit(self, pnl: float):
        """Updates portfolio equity upon trade exit"""
        self.cash += pnl
        self.equity_curve.append(self.cash)
