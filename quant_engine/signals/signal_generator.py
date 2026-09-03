"""
==============================================================================
  QUANT ENGINE — SIGNAL GENERATION & EDGE EVALUATION ENGINE
==============================================================================
"""

class SignalEngine:
    def __init__(self, fee_pct=0.0015, slippage_pct=0.0010):
        self.total_cost_threshold = fee_pct + slippage_pct

    def generate_signal(self, predictions: dict) -> dict:
        """Converts neural network predictions into actionable trading signals"""
        prob_up   = predictions.get("prob_up", 0.5)
        exp_ret   = predictions.get("expected_return", 0.0) / 100.0
        conf      = predictions.get("confidence", 0.5)

        # Net Edge = Expected Return - Transaction Costs - Slippage
        net_edge = exp_ret - self.total_cost_threshold

        if prob_up >= 0.65 and net_edge > 0.005 and conf >= 0.60:
            signal = "LONG"
        elif prob_up <= 0.35 and abs(exp_ret) > self.total_cost_threshold and conf >= 0.60:
            signal = "SHORT"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "prob_long": round(prob_up, 2),
            "prob_short": round(1.0 - prob_up, 2),
            "prob_hold": round(abs(0.5 - prob_up), 2),
            "net_edge_pct": round(net_edge * 100.0, 2),
            "is_actionable": signal != "HOLD"
        }
