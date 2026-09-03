"""
==============================================================================
  QUANT ENGINE — BROKER ADAPTER ABSTRACT INTERFACE
==============================================================================
"""

from abc import ABC, abstractmethod

class BrokerInterface(ABC):
    @abstractmethod
    def execute_order(self, symbol: str, side: str, amount: float, price: float = None) -> dict:
        pass

    @abstractmethod
    def get_positions(self) -> list:
        pass

    @abstractmethod
    def cancel_all_orders(self) -> bool:
        pass
