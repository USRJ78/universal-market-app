import sys
import os
import time
import json
import logging

# Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError on Windows terminals when printing emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from datetime import datetime
import pandas as pd
import numpy as np

# Try to import ccxt safely
try:
    import ccxt
except ImportError:
    ccxt = None

STATE_FILE = "funding_arb_state.json"
LOG_FILE = "funding_arb.log"
EXCEL_FILE = "funding_arb_execution_log.xlsx"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FundingArbBot")

class FundingArbBot:
    def __init__(self, start_capital=1000.0, min_apr_trigger=8.0, stop_apr_trigger=2.0):
        self.capital = start_capital
        self.balance_usdt = start_capital
        self.total_trades = 0
        self.total_yield = 0.0
        self.cycles_scanned = 0
        self.positions = []
        self.trades = []
        self.status = "stopped"
        
        # Configuration thresholds
        self.min_apr_trigger = min_apr_trigger # 8% APR to open
        self.stop_apr_trigger = stop_apr_trigger # 2% APR to close/unwind
        self.position_allocation = 250.0 # allocation size per active asset ($)
        
        # Load state if available
        self.load_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.capital = state.get("capital", 1000.0)
                self.balance_usdt = state.get("balance_usdt", 1000.0)
                self.total_trades = state.get("total_trades", 0)
                self.total_yield = state.get("total_yield", 0.0)
                self.cycles_scanned = state.get("cycles_scanned", 0)
                self.positions = state.get("positions", [])
                self.trades = state.get("trades", [])
                self.status = state.get("status", "stopped")
                self.min_apr_trigger = state.get("min_apr_trigger", 8.0)
                self.stop_apr_trigger = state.get("stop_apr_trigger", 2.0)
                self.position_allocation = state.get("position_allocation", 250.0)
                logger.info("Funding bot state successfully loaded from JSON.")
            except Exception as e:
                logger.error(f"Error loading bot state: {e}")

    def save_state(self):
        state = {
            "capital": self.capital,
            "balance_usdt": self.balance_usdt,
            "total_trades": self.total_trades,
            "total_yield": self.total_yield,
            "cycles_scanned": self.cycles_scanned,
            "positions": self.positions,
            "trades": self.trades[-50:], # Cache last 50 trades
            "status": self.status,
            "min_apr_trigger": self.min_apr_trigger,
            "stop_apr_trigger": self.stop_apr_trigger,
            "position_allocation": self.position_allocation,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving bot state: {e}")

    def open_position(self, asset, spot_price, perp_price, apr):
        # Check if cash available
        if self.balance_usdt < self.position_allocation:
            logger.warning(f"Insufficient cash to allocate position in {asset}. Cash: ${self.balance_usdt:.2f}")
            return
            
        self.balance_usdt -= self.position_allocation
        self.total_trades += 1
        
        pos = {
            "asset": asset,
            "spot_price": float(spot_price),
            "perp_price": float(perp_price),
            "size": float(self.position_allocation),
            "apr": float(apr),
            "yield_captured": 0.0,
            "opened_at": datetime.now().strftime("%H:%M:%S")
        }
        self.positions.append(pos)
        
        trade = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "asset": asset,
            "action": "OPEN",
            "size": float(self.position_allocation),
            "apr": float(apr),
            "profit": 0.0
        }
        self.trades.append(trade)
        logger.info(f"⚡ OPENED DELTA-NEUTRAL POSITION on {asset} | Size: ${self.position_allocation:.2f} | Entry Spot: ${spot_price:,.2f} | Entry Perp: ${perp_price:,.2f} | APR: {apr:.2f}%")
        self.log_to_excel()

    def close_position(self, idx, current_spot, current_perp):
        pos = self.positions.pop(idx)
        final_yield = pos["yield_captured"]
        
        # Calculate Spot vs Perp entry-exit basis difference (adds/subtracts slightly to profit)
        # Entry spread: Perp_entry - Spot_entry
        # Exit spread: Perp_exit - Spot_exit
        entry_spread_pct = (pos["perp_price"] - pos["spot_price"]) / pos["spot_price"]
        exit_spread_pct = (current_perp - current_spot) / current_spot
        basis_profit = pos["size"] * (entry_spread_pct - exit_spread_pct)
        
        # Net Trade Profit = Accrued Yield + Basis Profit
        net_profit = final_yield + basis_profit
        self.balance_usdt += pos["size"] + net_profit
        
        trade = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "asset": pos["asset"],
            "action": "CLOSE",
            "size": pos["size"],
            "apr": pos["apr"],
            "profit": round(net_profit, 4)
        }
        self.trades.append(trade)
        logger.info(f"🛡️ CLOSED DELTA-NEUTRAL POSITION on {pos['asset']} | Realized Yield: ${final_yield:+.4f} | Basis Profit: ${basis_profit:+.4f} | Net Trade Profit: ${net_profit:+.4f}")
        self.log_to_excel()

    def log_to_excel(self):
        try:
            summary_df = pd.DataFrame(self.trades)
            param_df = pd.DataFrame([
                {"Parameter": "Starting Capital", "Value": self.capital},
                {"Parameter": "Active Balance", "Value": self.balance_usdt},
                {"Parameter": "Min APR Trigger (%)", "Value": self.min_apr_trigger},
                {"Parameter": "Stop APR Trigger (%)", "Value": self.stop_apr_trigger},
                {"Parameter": "Size per Position ($)", "Value": self.position_allocation}
            ])
            with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
                summary_df.to_excel(writer, sheet_name="Funding_Arb_Ledger", index=False)
                param_df.to_excel(writer, sheet_name="Config", index=False)
        except Exception as e:
            logger.error(f"Error exporting funding trades to Excel: {e}")

    def run_one_cycle(self, exchange):
        self.cycles_scanned += 1
        
        # Core assets to scan
        assets = ["BTC", "ETH", "SOL", "ADA", "XRP"]
        
        # 1. Fetch Price Tickers and Funding Rates
        live_data = {}
        try:
            if exchange:
                # CCXT Swap markets
                for asset in assets:
                    spot_symbol = f"{asset}/USDT"
                    perp_symbol = f"{asset}/USDT:USDT"
                    
                    spot_ticker = exchange.fetch_ticker(spot_symbol)
                    perp_ticker = exchange.fetch_ticker(perp_symbol)
                    
                    # Fetch swap funding rate
                    funding_info = exchange.fetch_funding_rate(perp_symbol)
                    raw_funding = funding_info.get("fundingRate", 0.0)
                    
                    # Annualize APR: rate * 3 * 365 * 100
                    apr = raw_funding * 3 * 365 * 100.0
                    
                    live_data[asset] = {
                        "spot": spot_ticker["close"],
                        "perp": perp_ticker["close"],
                        "apr": apr,
                        "rate": raw_funding
                    }
            else:
                # High-fidelity Market Regime Cycle Simulator
                # Cycles shift every 15 iterations (~30 seconds) to demonstrate active portfolio turnovers
                regime_cycle = (self.cycles_scanned // 15) % 3
                
                mock_baselines = {"BTC": 68000.0, "ETH": 3800.0, "SOL": 165.0, "ADA": 0.48, "XRP": 0.52}
                mock_aprs = {}
                
                if regime_cycle == 0:
                    # Regime 0: Bull Market (Sky-High Funding Rates) -> Triggers Opens across BTC, ETH, SOL, ADA
                    mock_aprs = {
                        "BTC": 16.5 + np.random.normal(0, 0.5),
                        "ETH": 14.2 + np.random.normal(0, 0.4),
                        "SOL": 22.8 + np.random.normal(0, 1.0),
                        "ADA": 9.4 + np.random.normal(0, 0.3),
                        "XRP": 5.1 + np.random.normal(0, 0.2)
                    }
                elif regime_cycle == 1:
                    # Regime 1: Neutral/Sideways Market (Moderate Rates) -> ADA / XRP unwind
                    mock_aprs = {
                        "BTC": 7.2 + np.random.normal(0, 0.3),
                        "ETH": 6.1 + np.random.normal(0, 0.2),
                        "SOL": 9.8 + np.random.normal(0, 0.5),
                        "ADA": 1.4 + np.random.normal(0, 0.1), # drops below stop trigger
                        "XRP": 0.8 + np.random.normal(0, 0.1)  # drops below stop trigger
                    }
                else:
                    # Regime 2: Bear Market (Near Zero / Negative Funding) -> Unwinds all assets completely!
                    mock_aprs = {
                        "BTC": 0.8 + np.random.normal(0, 0.1),  # drops below stop trigger
                        "ETH": -1.5 + np.random.normal(0, 0.2), # negative funding / unwind
                        "SOL": 1.1 + np.random.normal(0, 0.1),  # drops below stop trigger
                        "ADA": -0.8 + np.random.normal(0, 0.1),
                        "XRP": -0.4 + np.random.normal(0, 0.1)
                    }
                
                for asset in assets:
                    base = mock_baselines[asset]
                    # Induce slight spot vs perp spread differences to generate basis profits on close
                    spot_p = base + np.random.normal(0, base * 0.0005)
                    # Perp price is spot * (1.0 + random basis spread)
                    perp_p = spot_p * (1.0 + np.random.normal(0.0008, 0.0002))
                    apr = mock_aprs[asset]
                    
                    live_data[asset] = {
                        "spot": spot_p,
                        "perp": perp_p,
                        "apr": apr,
                        "rate": apr / (3 * 365 * 100.0)
                    }
        except Exception as e:
            logger.error(f"Error fetching live pricing/funding rate tickers: {e}")
            return

        # 2. Accrue Yield for active positions pro-rata
        # The loop runs every 2.0 seconds
        loop_interval = 2.0
        seconds_in_year = 365 * 24 * 3600
        for pos in self.positions:
            # Yield = size * (apr / 100) * (loop_interval / seconds_in_year)
            accrued = pos["size"] * (pos["apr"] / 100.0) * (loop_interval / seconds_in_year)
            pos["yield_captured"] += accrued
            self.total_yield += accrued
            # We don't credit cash balance until position unwinds (unrealized until exit)
            
        # Update current pricing and APR in positions list
        for pos in self.positions:
            asset = pos["asset"]
            if asset in live_data:
                # Update APR in position dynamically
                pos["apr"] = live_data[asset]["apr"]

        # 3. Print operational status every 5 cycles
        if self.cycles_scanned % 5 == 0:
            active_assets = [p["asset"] for p in self.positions]
            logger.info(f"Scan Loop #{self.cycles_scanned} | Active Positions: {active_assets} | Cumulative Yield: ${self.total_yield:.6f}")
            for asset, d in live_data.items():
                logger.info(f"  · {asset:<4} | Spot: ${d['spot']:,.2f} | Perp: ${d['perp']:,.2f} | Funding APR: {d['apr']:.2f}%")

        # 4. Position Management Layer (Check Open/Close Triggers)
        # Check unwind first (close if APR falls below threshold)
        for i in reversed(range(len(self.positions))):
            pos = self.positions[i]
            asset = pos["asset"]
            if asset in live_data:
                current_apr = live_data[asset]["apr"]
                if current_apr < self.stop_apr_trigger:
                    logger.info(f"⚠️ APR drop detected on {asset}! Current APR: {current_apr:.2f}% < Exit trigger: {self.stop_apr_trigger:.2f}%. Unwinding position...")
                    self.close_position(i, live_data[asset]["spot"], live_data[asset]["perp"])

        # Check open (if APR exceeds threshold and position not already held)
        active_assets = [p["asset"] for p in self.positions]
        for asset, d in live_data.items():
            if asset not in active_assets:
                if d["apr"] >= self.min_apr_trigger:
                    logger.info(f"💥 HIGH YIELD SPOT! {asset} Funding APR: {d['apr']:.2f}% >= Entry trigger: {self.min_apr_trigger:.2f}%. Opening position...")
                    self.open_position(asset, d["spot"], d["perp"], d["apr"])

def run_funding_bot():
    logger.info("Initializing Live Funding Rate Arbitrage Daemon...")
    
    # Initialize CCXT exchange client safely
    exchange = None
    if ccxt:
        try:
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'} # Perpetual swap markets
            })
            exchange.load_markets()
            logger.info("CCXT Perpetual Futures Client Initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to connect to CCXT Swap Exchange: {e}. Bot will operate in simulation mode.")
            exchange = None
    else:
        logger.warning("CCXT library missing. Bot will operate in simulation mode.")
        
    bot = FundingArbBot()
    bot.status = "running"
    bot.save_state()
    
    logger.info(f"Funding Bot RUNNING | Start Capital: ${bot.capital:,.2f} | Entry APR trigger: {bot.min_apr_trigger}% | Exit APR trigger: {bot.stop_apr_trigger}%")
    
    while True:
        # Check command loop state from json
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("status") == "stopped":
                    logger.info("Halt command intercepted. Stopping funding arbitrage loop cleanly...")
                    break
            except Exception:
                pass
                
        bot.run_one_cycle(exchange)
        bot.save_state()
        time.sleep(2.0) # 2 seconds scan refresh rate
        
    bot.status = "stopped"
    bot.save_state()
    logger.info("Funding trading daemon safely stopped.")

if __name__ == "__main__":
    run_funding_bot()
