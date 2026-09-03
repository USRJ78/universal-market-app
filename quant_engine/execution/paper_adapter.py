"""
==============================================================================
  QUANT ENGINE — PAPER TRADING EXECUTION ADAPTER (DEFAULT)
==============================================================================
"""

import time, uuid, datetime
from quant_engine.execution.broker_interface import BrokerInterface

class PaperExecutionAdapter(BrokerInterface):
    def __init__(self, fee_pct=0.0015, slippage_pct=0.0010):
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.open_positions = []
        self.executed_trades = []

    def execute_order(self, symbol: str, side: str, amount: float, price: float = None) -> dict:
        """Simulates realistic paper trade execution with fee & slippage deductions"""
        exec_price = price * (1.0 + self.slippage_pct if side == "BUY" else 1.0 - self.slippage_pct)
        fees = amount * self.fee_pct
        
        trade_record = {
            "order_id": f"PAPER-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": exec_price,
            "fees": fees,
            "status": "FILLED",
            "mode": "PAPER"
        }

        self.executed_trades.append(trade_record)
        return trade_record

    def get_positions(self) -> list:
        return self.open_positions

    def cancel_all_orders(self) -> bool:
        return True
