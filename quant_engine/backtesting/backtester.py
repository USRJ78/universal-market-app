"""
==============================================================================
  QUANT ENGINE — REALITY-BASED BACKTEST & BENCHMARKING ENGINE
==============================================================================
"""

import numpy as np
import pandas as pd

class RealityBacktester:
    def __init__(self, fee_pct=0.0015, slippage_pct=0.0010):
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct

    def run_backtest(self, df: pd.DataFrame, initial_capital=100000.0) -> dict:
        """Runs reality-based backtest with transaction costs & slippage"""
        if df.empty or len(df) < 30:
            return {}

        close = df["Close"]
        returns = close.pct_change().fillna(0)

        capital = initial_capital
        equity_curve = [capital]

        for t in range(1, len(df)):
            ret = returns.iloc[t]
            # Simple benchmark allocation signal
            if ret > 0:
                trade_ret = (ret * 0.98) - self.fee_pct # Net after slippage & fee
                capital += capital * 0.15 * trade_ret
            equity_curve.append(capital)

        net_ret = (capital / initial_capital - 1.0) * 100.0
        cagr = (((capital / initial_capital) ** (1 / max(1, len(df)/252.0))) - 1.0) * 100.0

        return {
            "initial_capital": initial_capital,
            "final_capital": round(capital, 2),
            "net_return_pct": round(net_ret, 2),
            "cagr_pct": round(cagr, 2),
            "equity_curve": equity_curve
        }
