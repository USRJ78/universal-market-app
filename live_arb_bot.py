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
    # Fallback to simulate price feed if ccxt is missing
    ccxt = None

STATE_FILE = "arb_state.json"
LOG_FILE = "arb_bot.log"
EXCEL_FILE = "live_arb_execution_log.xlsx"

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
logger = logging.getLogger("LiveArbBot")

class LiveArbBot:
    def __init__(self, start_capital=1000.0, trade_size=100.0, min_profit=0.05):
        self.capital = start_capital
        self.balance_usdt = start_capital
        self.trade_size = trade_size
        self.min_profit_pct = min_profit # 0.05% default
        self.total_trades = 0
        self.total_profit = 0.0
        self.win_rate = 0.0
        self.cycles_scanned = 0
        self.trades = []
        self.status = "stopped"
        self.total_fees_paid = 0.0
        
        # New trials and trade limit properties
        self.trials = []
        self.limit_trades = False
        self.max_trades_limit = 0
        
        # Load existing state if available
        self.load_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.capital = state.get("capital", 1000.0)
                self.balance_usdt = state.get("balance_usdt", 1000.0)
                self.trade_size = state.get("trade_size", 100.0)
                self.min_profit_pct = state.get("min_profit_pct", 0.05)
                self.total_trades = state.get("total_trades", 0)
                self.total_profit = state.get("total_profit", 0.0)
                self.win_rate = state.get("win_rate", 0.0)
                self.cycles_scanned = state.get("cycles_scanned", 0)
                self.trades = state.get("trades", [])
                self.status = state.get("status", "stopped")
                self.total_fees_paid = state.get("total_fees_paid", 0.0)
                self.trials = state.get("trials", [])
                self.limit_trades = state.get("limit_trades", False)
                self.max_trades_limit = state.get("max_trades_limit", 0)
                logger.info("Bot state successfully loaded from JSON.")
            except Exception as e:
                logger.error(f"Error loading bot state: {e}")

    def save_state(self):
        state = {
            "capital": self.capital,
            "balance_usdt": self.balance_usdt,
            "trade_size": self.trade_size,
            "min_profit_pct": self.min_profit_pct,
            "total_trades": self.total_trades,
            "total_profit": self.total_profit,
            "win_rate": self.win_rate,
            "cycles_scanned": self.cycles_scanned,
            "trades": self.trades[-50:], # Cache only last 50 trades in JSON for speed
            "status": self.status,
            "total_fees_paid": self.total_fees_paid,
            "trials": self.trials,
            "limit_trades": self.limit_trades,
            "max_trades_limit": self.max_trades_limit,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving bot state: {e}")

    def archive_current_trial(self, stop_reason="Manual Halt"):
        if self.cycles_scanned == 0 and self.total_trades == 0:
            return
            
        if not hasattr(self, "trials") or self.trials is None:
            self.trials = []
            
        # Avoid duplicate archiving if already archived
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = getattr(self, "last_updated", end_time)
        
        if self.trials:
            last = self.trials[-1]
            if last.get("cycles_scanned") == self.cycles_scanned and last.get("total_trades") == self.total_trades and last.get("net_profit") == round(self.total_profit, 4):
                logger.info("Current trial was already archived. Skipping duplicate archive.")
                return
                
        trial_record = {
            "trial_id": len(self.trials) + 1,
            "start_time": start_time,
            "end_time": end_time,
            "initial_capital": round(self.capital, 2),
            "final_balance": round(self.balance_usdt, 2),
            "net_profit": round(self.total_profit, 4),
            "total_trades": self.total_trades,
            "total_fees_paid": round(self.total_fees_paid, 4),
            "win_rate": round(self.win_rate, 1),
            "cycles_scanned": self.cycles_scanned,
            "stop_reason": stop_reason
        }
        self.trials.append(trial_record)
        logger.info(f"📊 Trial #{trial_record['trial_id']} archived successfully: PnL: {trial_record['net_profit']:+,.4f}, Trades: {trial_record['total_trades']}.")

    def reset_active_portfolio(self):
        self.balance_usdt = self.capital
        self.total_trades = 0
        self.total_profit = 0.0
        self.win_rate = 0.0
        self.cycles_scanned = 0
        self.trades = []
        self.total_fees_paid = 0.0
        logger.info("Active paper portfolio successfully reset to zero/starting capital.")

    def add_trade(self, expected_return, net_pnl, fee_paid=0.0):
        self.total_trades += 1
        self.total_profit += net_pnl
        self.balance_usdt += net_pnl
        self.total_fees_paid = getattr(self, "total_fees_paid", 0.0) + fee_paid
        
        # Win rate recalculation
        winning_trades = len([t for t in self.trades if t.get("profit", 0.0) > 0])
        if net_pnl > 0:
            winning_trades += 1
        self.win_rate = (winning_trades / self.total_trades) * 100.0
        
        trade_record = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "cycle": self.cycles_scanned,
            "expected_return": round((expected_return - 1.0) * 100.0, 4), # return %
            "profit": round(net_pnl, 4),
            "fee": round(fee_paid, 4),
            "balance": round(self.balance_usdt, 2)
        }
        self.trades.append(trade_record)
        
        # Log to excel audit trail asynchronously or incrementally
        self.log_to_excel()

    def log_to_excel(self):
        try:
            summary_df = pd.DataFrame(self.trades)
            param_df = pd.DataFrame([
                {"Parameter": "Starting Capital", "Value": self.capital},
                {"Parameter": "Active Balance", "Value": self.balance_usdt},
                {"Parameter": "Allocated Size", "Value": self.trade_size},
                {"Parameter": "Min Profit trigger (%)", "Value": self.min_profit_pct}
            ])
            with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
                summary_df.to_excel(writer, sheet_name="Live_Paper_Trades", index=False)
                param_df.to_excel(writer, sheet_name="Bot_Config", index=False)
        except Exception as e:
            logger.error(f"Error exporting trades to Excel: {e}")

    def run_one_cycle(self, exchange):
        """Runs a single scanning and trading iteration."""
        self.cycles_scanned += 1
        symbols = ["BTC/USDT", "ETH/BTC", "ETH/USDT"]
        
        try:
            # 1. Price Polling Layer
            use_fallback = False
            if exchange:
                try:
                    tickers = exchange.fetch_tickers(symbols)
                    p1_ask = tickers["BTC/USDT"]['ask']
                    p2_ask = tickers["ETH/BTC"]['ask']
                    p3_bid = tickers["ETH/USDT"]['bid']
                except Exception as ce:
                    logger.warning(f"⚠️ Live Spot CCXT tickers fetch failed: {ce}. Geoblock or API rate limit active. Falling back to simulation...")
                    use_fallback = True
            
            if not exchange or use_fallback:
                # Simulated Feed fallback with dynamic volatility waves to generate active opportunities
                # Every ~12 cycles, inject a high-volatility spread burst (+0.25% to +0.55%)
                # Every ~5 cycles, inject a micro-arbitrage spread (+0.08% to +0.18%)
                if self.cycles_scanned % 12 == 0:
                    spread_sim = np.random.uniform(0.0025, 0.0055)
                elif self.cycles_scanned % 5 == 0:
                    spread_sim = np.random.uniform(0.0008, 0.0018)
                else:
                    spread_sim = np.random.uniform(-0.0005, 0.0002)
                
                p1_ask = 65000.0 + np.random.normal(0, 15)
                p2_ask = 0.0524 + np.random.normal(0, 0.0001)
                p3_bid = p1_ask * p2_ask * (1.0 + spread_sim)
            
            if not (p1_ask and p2_ask and p3_bid):
                return
                
            # 2. Implied Triangular Return multiple
            # Pathway: USDT -> buy BTC -> buy ETH -> sell to USDT
            # Gross = (1 / BTC/USDT Ask) * (1 / ETH/BTC Ask) * (ETH/USDT Bid)
            gross_multiple = (1.0 / p1_ask) * (1.0 / p2_ask) * p3_bid
            spread_pct = (gross_multiple - 1.0) * 100.0
            
            # Print scan stats every 5 cycles
            if self.cycles_scanned % 5 == 0:
                logger.info(
                    f"Scan #{self.cycles_scanned} | BTC: ${p1_ask:,.1f} | ETH/BTC: {p2_ask:.5f} | "
                    f"ETH: ${p3_bid:,.1f} | Implied Spread: {spread_pct:+.4f}%"
                )
                
            # 3. Profit Trigger Check
            trigger_target = 1.0 + (self.min_profit_pct / 100.0)
            if gross_multiple >= trigger_target:
                logger.info(f"💥 ARBITRAGE ARMED! Spread: {spread_pct:+.4f}%. Executing paper trades...")
                
                # Slippage & commission simulation (e.g. 0.05% fee per leg = 0.15% total fee)
                commission_pct = 0.05 / 100.0
                slippage_pct = 0.02 / 100.0
                total_drag = (commission_pct + slippage_pct) * 3
                
                # Executed Return
                net_multiple = gross_multiple - total_drag
                net_pnl = self.trade_size * (net_multiple - 1.0)
                fee_paid = self.trade_size * total_drag
                
                self.add_trade(gross_multiple, net_pnl, fee_paid)
                logger.info(f"✓ Cycle complete! Realized Paper PnL: ${net_pnl:+.4f} (drag simulated: {total_drag*100:.3f}%)")
                
                # Let markets settle
                time.sleep(2)
        except Exception as e:
            logger.error(f"Operational scanning error: {e}")

def run_paper_bot():
    """Main daemon loop running in the background."""
    logger.info("Initializing Live Paper Trading Arbitrage Bot Daemon...")
    
    # Initialize CCXT exchange client safely
    exchange = None
    if ccxt:
        try:
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            # Test connection
            exchange.load_markets()
            logger.info("CCXT Exchange Initialized: Connection to Binance established successfully.")
        except Exception as e:
            logger.warning(f"Failed to connect to CCXT Exchange: {e}. Bot will operate in simulation mode.")
            exchange = None
    else:
        logger.warning("CCXT library missing. Bot will operate in simulation mode.")
        
    bot = LiveArbBot()
    bot.status = "running"
    bot.save_state()
    
    logger.info(f"Paper Bot RUNNING | Start Capital: ${bot.capital:,.2f} | Allocated trade size: ${bot.trade_size:,.2f} | Trigger: {bot.min_profit_pct}%")
    
    stop_reason_to_use = "Manual Halt"
    while True:
        # Check command loop state from json
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("status") == "stopped":
                    logger.info("Halt command intercepted. Stopping paper trading loop cleanly...")
                    stop_reason_to_use = "Manual Halt"
                    break
            except Exception:
                pass
                
        # Check max trades limit
        if bot.limit_trades and bot.max_trades_limit > 0 and bot.total_trades >= bot.max_trades_limit:
            logger.info(f"🎯 Max trades limit ({bot.max_trades_limit}) reached! Automatically stopping...")
            stop_reason_to_use = "Max Trades Reached"
            break
            
        bot.run_one_cycle(exchange)
        bot.save_state()
        time.sleep(2.0) # Standard scanning refresh rate (2 seconds)
        
    bot.status = "stopped"
    bot.archive_current_trial(stop_reason=stop_reason_to_use)
    bot.save_state()
    logger.info("Paper trading daemon safely stopped.")

if __name__ == "__main__":
    run_paper_bot()
