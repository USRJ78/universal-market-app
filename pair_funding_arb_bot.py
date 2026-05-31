# pair_funding_arb_bot.py
import sys
import os
import time
import json
import logging
from datetime import datetime, timezone

# Reconfigure stdout to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import ccxt
except ImportError:
    ccxt = None

STATE_FILE = "pair_funding_arb_state.json"
LOG_FILE = "pair_funding_arb.log"
EXCEL_FILE = "pair_funding_arb_execution_log.xlsx"

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
logger = logging.getLogger("PairFundingArbBot")

def load_secrets():
    """
    Parses secrets.toml securely to fetch Binance credentials
    """
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            api_key = ""
            api_secret = ""
            for line in lines:
                if "=" in line and not line.strip().startswith("#"):
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    if key == "BINANCE_API_KEY":
                        api_key = val
                    elif key == "BINANCE_API_SECRET":
                        api_secret = val
            return api_key, api_secret
        except Exception as e:
            logger.error(f"Error parsing secrets.toml: {e}")
    return "", ""

# Default highly correlated pairs for Double-Sided Arbitrage
DEFAULT_PAIRS = [
    {"name": "BCH vs LTC", "long": "BCH", "short": "LTC"},
    {"name": "LTC vs BCH", "long": "LTC", "short": "BCH"},
    {"name": "L1 Aptos vs Sui", "long": "APT", "short": "SUI"},
    {"name": "L1 Sui vs Aptos", "long": "SUI", "short": "APT"},
    {"name": "L2 Optimism vs Arbitrum", "long": "ARB", "short": "OP"},
    {"name": "L2 Arbitrum vs Optimism", "long": "OP", "short": "ARB"},
    {"name": "Staking LDO vs Ethereum", "long": "LDO", "short": "ETH"},
    {"name": "Staking ETH vs LDO", "long": "ETH", "short": "LDO"}
]

class PairFundingArbBot:
    def __init__(self, start_capital=1000.0, min_apr_trigger=10.0):
        self.capital = start_capital
        self.balance_usdt = start_capital
        self.total_trades = 0
        self.cycles_scanned = 0
        self.positions = []
        self.trades = []
        self.status = "stopped"
        
        # Configuration thresholds
        self.min_apr_trigger = min_apr_trigger # 10% Combined APR spread
        self.position_allocation = 250.0 # allocation size per active pair ($)
        self.futures_leverage = 5.0 # default 5x futures leverage
        
        # Credentials
        self.execution_mode = "paper" # "paper" or "live"
        self.api_key = ""
        self.api_secret = ""
        
        self.exchange = None
        self.total_fees_paid = 0.0
        self.trials = []
        
        # Pull credentials from secrets.toml by default
        self.api_key, self.api_secret = load_secrets()
        
        self.load_state()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.capital = state.get("capital", 1000.0)
                self.balance_usdt = state.get("balance_usdt", 1000.0)
                self.total_trades = state.get("total_trades", 0)
                self.cycles_scanned = state.get("cycles_scanned", 0)
                self.positions = state.get("positions", [])
                self.trades = state.get("trades", [])
                self.status = state.get("status", "stopped")
                self.min_apr_trigger = state.get("min_apr_trigger", 10.0)
                self.position_allocation = state.get("position_allocation", 250.0)
                self.futures_leverage = state.get("futures_leverage", 5.0)
                self.total_fees_paid = state.get("total_fees_paid", 0.0)
                self.trials = state.get("trials", [])
                self.execution_mode = state.get("execution_mode", "paper")
                
                # Restore API keys if missing in state but present in secrets
                s_key, s_sec = load_secrets()
                self.api_key = state.get("api_key", s_key)
                self.api_secret = state.get("api_secret", s_sec)
                
                logger.info("Pair Funding state successfully loaded from JSON.")
            except Exception as e:
                logger.error(f"Error loading bot state: {e}")

    def save_state(self):
        state = {
            "capital": self.capital,
            "balance_usdt": self.balance_usdt,
            "total_trades": self.total_trades,
            "cycles_scanned": self.cycles_scanned,
            "positions": self.positions,
            "trades": self.trades[-50:],
            "status": self.status,
            "min_apr_trigger": self.min_apr_trigger,
            "position_allocation": self.position_allocation,
            "futures_leverage": self.futures_leverage,
            "total_fees_paid": self.total_fees_paid,
            "trials": self.trials,
            "execution_mode": self.execution_mode,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving bot state: {e}")

    def init_exchanges(self):
        if self.execution_mode == "live" and self.api_key and self.api_secret:
            if ccxt is None:
                logger.error("CCXT library missing. Cannot initialize live trading.")
                return
            try:
                self.exchange = ccxt.binance({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'swap'} # Perpetual swap markets
                })
                self.exchange.load_markets()
                logger.info("🔑 Binance LIVE Swap Client initialized successfully using Streamlit Secrets credentials.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize live Binance swap client: {e}. Falling back to simulation.")
                self.exchange = None
        else:
            self.exchange = None

    def open_pair_position(self, pair_name, long_asset, short_asset, long_rate, short_rate, long_apr, short_apr, long_price, short_price, funding_time_ms):
        # Margin per leg = position allocation / 2
        M_leg = self.position_allocation / 2.0
        L = self.futures_leverage
        
        # Position Size ($) per leg is margin * leverage
        S = M_leg * L
        
        # Entry fees (0.05% taker perp entry fee per leg)
        open_fee = S * 0.0010 # 0.05% * 2 legs
        total_cash_needed = self.position_allocation + open_fee
        
        if self.balance_usdt < total_cash_needed:
            logger.warning(f"Insufficient cash to allocate pair {pair_name}. Cash: ${self.balance_usdt:.2f}, Required: ${total_cash_needed:.2f}")
            return
            
        real_execution = False
        order_ids = []
        filled_long_price = long_price
        filled_short_price = short_price
        
        if self.execution_mode == "live" and self.exchange:
            l_sym = f"{long_asset}/USDT:USDT"
            s_sym = f"{short_asset}/USDT:USDT"
            
            qty_long = S / long_price
            qty_short = S / short_price
            
            # Format to precision lot size
            try:
                qty_long_rounded = float(self.exchange.amount_to_precision(l_sym, qty_long))
                qty_short_rounded = float(self.exchange.amount_to_precision(s_sym, qty_short))
                logger.info(f"Lot Precision: Long {long_asset} qty: {qty_long_rounded:.6f} | Short {short_asset} qty: {qty_short_rounded:.6f}")
            except Exception as err:
                logger.error(f"Precision error: {err}. Falling back to default rounding.")
                qty_long_rounded = round(qty_long, 4)
                qty_short_rounded = round(qty_short, 4)
                
            try:
                # 1. Open Long leg (Market Buy)
                logger.info(f"⚡ [LIVE TRADE] Setting {long_asset} leverage to {int(L)}x...")
                self.exchange.set_leverage(int(L), l_sym)
                time.sleep(0.1)
                
                logger.info(f"⚡ [LIVE TRADE] Executing Leg 1 (Long): Market Buy {qty_long_rounded} {long_asset}...")
                order_long = self.exchange.create_market_buy_order(l_sym, qty_long_rounded)
                order_ids.append(order_long.get("id", "Long-Real"))
                
                filled_long_price = float(order_long.get("price", long_price) or long_price)
                if filled_long_price <= 0.0:
                    filled_long_price = long_price
                logger.info(f"✅ Long Leg filled at ${filled_long_price:,.4f}")
            except Exception as e1:
                logger.error(f"❌ Live Leg 1 (Long Buy) failed: {e1}. Aborting pair.")
                return
                
            try:
                # 2. Open Short leg (Market Sell/Short)
                logger.info(f"⚡ [LIVE TRADE] Setting {short_asset} leverage to {int(L)}x...")
                self.exchange.set_leverage(int(L), s_sym)
                time.sleep(0.1)
                
                logger.info(f"⚡ [LIVE TRADE] Executing Leg 2 (Short): Market Sell {qty_short_rounded} {short_asset}...")
                order_short = self.exchange.create_market_sell_order(s_sym, qty_short_rounded)
                order_ids.append(order_short.get("id", "Short-Real"))
                
                filled_short_price = float(order_short.get("price", short_price) or short_price)
                if filled_short_price <= 0.0:
                    filled_short_price = short_price
                logger.info(f"✅ Short Leg filled at ${filled_short_price:,.4f}")
                real_execution = True
            except Exception as e2:
                logger.critical(f"❌ Live Leg 2 (Short Sell) failed: {e2}. UNHEDGED DIRECTION RISK! Rolling back Long Leg 1 instantly...")
                try:
                    rollback_order = self.exchange.create_market_sell_order(l_sym, qty_long_rounded)
                    logger.info(f"🛡️ Rollback executed successfully! Long sold back. Order ID: {rollback_order.get('id', 'Rollback')}")
                except Exception as er:
                    logger.error(f"🚨 CRITICAL WARNING: SPOT ROLLBACK FAILED! Manually close {long_asset} Long immediately! Error: {er}")
                return
        else:
            # Paper mode operates on 100% genuine live prices fetched
            real_execution = True
            
        if real_execution:
            self.balance_usdt -= total_cash_needed
            self.total_fees_paid += open_fee
            self.total_trades += 1
            
            pos = {
                "pair_name": pair_name,
                "long_asset": long_asset,
                "short_asset": short_asset,
                "margin_allocated": float(self.position_allocation),
                "leverage": float(L),
                "position_size": float(S),
                "long_entry_price": float(filled_long_price),
                "short_entry_price": float(filled_short_price),
                "long_rate": float(long_rate),
                "short_rate": float(short_rate),
                "long_apr": float(long_apr),
                "short_apr": float(short_apr),
                "funding_time_ms": funding_time_ms,
                "funding_received": 0.0,
                "settled": False,
                "opened_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            if order_ids:
                pos["orders"] = order_ids
                
            self.positions.append(pos)
            
            trade = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "pair": pair_name,
                "action": "OPEN",
                "size": float(self.position_allocation),
                "combined_apr": float(short_apr - long_apr),
                "profit": 0.0,
                "fee": round(open_fee, 4)
            }
            if order_ids:
                trade["orders"] = order_ids
            self.trades.append(trade)
            logger.info(f"⚡ OPENED TACTICAL DOUBLE-SIDED PAIR POSITION: {pair_name} | Size: ${self.position_allocation:.2f} | Long {long_asset} Entry: ${filled_long_price:,.4f} | Short {short_asset} Entry: ${filled_short_price:,.4f} | Est. Combined APR: {(short_apr - long_apr):.2f}%")
            self.save_state()

    def close_pair_position(self, idx, current_long_price, current_short_price):
        pos = self.positions.pop(idx)
        S = pos["position_size"]
        M = pos["margin_allocated"]
        pair_name = pos["pair_name"]
        long_asset = pos["long_asset"]
        short_asset = pos["short_asset"]
        
        # Exit commission fees (0.05% per leg close)
        close_fee = S * 0.0010
        self.total_fees_paid += close_fee
        
        filled_long_exit = current_long_price
        filled_short_exit = current_short_price
        order_ids = []
        
        if self.execution_mode == "live" and self.exchange:
            l_sym = f"{long_asset}/USDT:USDT"
            s_sym = f"{short_asset}/USDT:USDT"
            
            qty_long = S / pos["long_entry_price"]
            qty_short = S / pos["short_entry_price"]
            
            try:
                qty_long_rounded = float(self.exchange.amount_to_precision(l_sym, qty_long))
                qty_short_rounded = float(self.exchange.amount_to_precision(s_sym, qty_short))
            except Exception:
                qty_long_rounded = round(qty_long, 4)
                qty_short_rounded = round(qty_short, 4)
                
            # 1. Close Long (Market Sell)
            try:
                logger.info(f"🛡️ [LIVE TRADE] Executing Leg 1 Close: Market Sell {qty_long_rounded} {long_asset}...")
                order_long = self.exchange.create_market_sell_order(l_sym, qty_long_rounded)
                order_ids.append(order_long.get("id", "Long-Close-Real"))
                
                filled_long_exit = float(order_long.get("price", current_long_price) or current_long_price)
                if filled_long_exit <= 0.0:
                    filled_long_exit = current_long_price
                logger.info(f"✅ Long Leg closed at ${filled_long_exit:,.4f}")
            except Exception as e1:
                logger.error(f"🚨 CRITICAL WARNING: Live Long Close failed: {e1}. Please manually market sell {long_asset} Swap immediately!")
                
            # 2. Close Short (Market Buy Cover)
            try:
                logger.info(f"🛡️ [LIVE TRADE] Executing Leg 2 Close: Market Buy Cover {qty_short_rounded} {short_asset}...")
                order_short = self.exchange.create_market_buy_order(s_sym, qty_short_rounded)
                order_ids.append(order_short.get("id", "Short-Close-Real"))
                
                filled_short_exit = float(order_short.get("price", current_short_price) or current_short_price)
                if filled_short_exit <= 0.0:
                    filled_short_exit = current_short_price
                logger.info(f"✅ Short Leg covered at ${filled_short_exit:,.4f}")
            except Exception as e2:
                logger.error(f"🚨 CRITICAL WARNING: Live Short Close failed: {e2}. Please manually market cover {short_asset} Swap immediately!")
        
        # Calculate asset-basis spread convergence profit
        # Long PnL = S * (Exit Price - Entry Price) / Entry Price
        long_pnl_pct = (filled_long_exit - pos["long_entry_price"]) / pos["long_entry_price"]
        long_profit = S * long_pnl_pct
        
        # Short PnL = S * (Entry Price - Exit Price) / Entry Price
        short_pnl_pct = (pos["short_entry_price"] - filled_short_exit) / pos["short_entry_price"]
        short_profit = S * short_pnl_pct
        
        basis_profit = long_profit + short_profit
        
        # Total profit is funding received + basis profit
        funding_yield = pos["funding_received"]
        net_profit = funding_yield + basis_profit
        
        cash_returned = M + net_profit - close_fee
        self.balance_usdt += cash_returned
        
        trade = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "pair": pair_name,
            "action": "CLOSE",
            "size": M,
            "combined_apr": float(pos["short_apr"] - pos["long_apr"]),
            "profit": round(net_profit, 4),
            "fee": round(close_fee, 4)
        }
        if order_ids:
            trade["orders"] = order_ids
        self.trades.append(trade)
        
        logger.info(f"🛡️ CLOSED TACTICAL PAIR POSITION: {pair_name} | Captured Funding Fee: ${funding_yield:+.4f} | Basis Convergence: ${basis_profit:+.4f} | Net Trade Profit: ${net_profit:+.4f} | Total Fee: ${close_fee:.4f}")
        self.save_state()

    def run_one_cycle(self, public_exchange):
        self.cycles_scanned += 1
        
        # Assets to monitor
        assets = list(set([p["long"] for p in DEFAULT_PAIRS] + [p["short"] for p in DEFAULT_PAIRS]))
        
        # 1. Fetch live Binance perpetual swap prices & funding rates
        live_data = {}
        use_fallback = False
        now_ms = time.time() * 1000
        
        try:
            if public_exchange:
                perp_symbols = [f"{asset}/USDT:USDT" for asset in assets]
                tickers = public_exchange.fetch_tickers(perp_symbols)
                
                # Fetch/Cache funding rates
                raw_rates = public_exchange.fetch_funding_rates(perp_symbols)
                
                for asset in assets:
                    sym = f"{asset}/USDT:USDT"
                    close_p = tickers.get(sym, {}).get("close")
                    rate_info = raw_rates.get(sym, {})
                    rate = rate_info.get("fundingRate", 0.0001)
                    funding_time = rate_info.get("fundingTime")
                    
                    apr = rate * 3 * 365 * 100.0 # standard 8-hour payments
                    
                    if close_p:
                        countdown_sec = 0.0
                        if funding_time:
                            countdown_sec = max(0.0, (funding_time - now_ms) / 1000.0)
                            
                        live_data[asset] = {
                            "price": close_p,
                            "rate": rate,
                            "apr": apr,
                            "funding_time_ms": funding_time,
                            "countdown_seconds": countdown_sec
                        }
        except Exception as e:
            logger.warning(f"⚠️ Live CCXT scan failed: {e}. Falling back to high-fidelity market regime simulation...")
            use_fallback = True
            
        if not public_exchange or use_fallback:
            # High-fidelity real-time simulation
            mock_prices = {"BTC": 68000.0, "ETH": 3800.0, "SOL": 165.0, "AVAX": 36.0, "APT": 9.2, "SUI": 1.15, "OP": 2.25, "ARB": 0.95, "BCH": 480.0, "LTC": 82.0, "LDO": 1.85}
            mock_rates = {
                "BTC": 0.0001, "ETH": 0.00015, "SOL": 0.0002, 
                "AVAX": 0.0001, "APT": -0.00012, "SUI": 0.00018, 
                "OP": 0.00025, "ARB": -0.00008, "BCH": -0.00035, 
                "LTC": 0.00005, "LDO": -0.0001
            }
            
            for asset in assets:
                base = mock_prices.get(asset, 50.0)
                # Float prices slightly to keep it extremely realistic
                price = base + (time.time() % 10 - 5) * 0.001 * base
                rate = mock_rates.get(asset, 0.0001)
                
                # Mock countdown settling boundary (crossovers happen every 4 minutes in sandbox simulator for rich visuals!)
                time_in_cycle = int(time.time()) % 240
                countdown_sec = 240 - time_in_cycle
                funding_time = (time.time() + countdown_sec) * 1000
                
                live_data[asset] = {
                    "price": price,
                    "rate": rate,
                    "apr": rate * 3 * 365 * 100.0,
                    "funding_time_ms": funding_time,
                    "countdown_seconds": countdown_sec
                }
                
        # 2. Sync real balances in live mode
        if self.execution_mode == "live" and self.exchange:
            try:
                bal = self.exchange.fetch_balance()
                self.balance_usdt = bal.get("USDT", {}).get("free", self.balance_usdt)
            except Exception as e:
                logger.error(f"Failed to sync live wallet balance: {e}")

        # 3. Position Crossover Management (Accrue yield at boundary crossover)
        for pos in self.positions:
            long_asset = pos["long_asset"]
            short_asset = pos["short_asset"]
            
            if long_asset in live_data and short_asset in live_data:
                # Check if countdown has crossed over / rolled forward
                # In simulation mode, crossover is when countdown reaches 240
                # In live mode, crossover is when current time exceeds the stored funding_time_ms
                current_time_ms = time.time() * 1000
                
                if not pos["settled"] and current_time_ms >= pos["funding_time_ms"]:
                    # Settlement crossed! Collect double-sided funding fee
                    # Long pays long_rate -> if rate is negative, Long receives positive payment: -rate * S
                    long_yield = -pos["long_rate"] * pos["position_size"]
                    # Short receives short_rate -> short_rate * S
                    short_yield = pos["short_rate"] * pos["position_size"]
                    
                    total_yield = long_yield + short_yield
                    pos["funding_received"] += total_yield
                    pos["settled"] = True
                    logger.info(f"🎉 FUNDING INTERACTION CROSSOVER REACHED for {pos['pair_name']}! Received Long leg: ${long_yield:+.4f} | Short leg: ${short_yield:+.4f} | Total Captured: ${total_yield:+.4f}")
                    self.save_state()

        # 4. Tactical Auto-Trigger Unwinds (Exit 2 minutes / 120 seconds after crossover)
        for i in reversed(range(len(self.positions))):
            pos = self.positions[i]
            if pos["settled"]:
                current_time_ms = time.time() * 1000
                # Exit exactly 2 minutes (120 seconds) after settlement crossover
                if current_time_ms >= pos["funding_time_ms"] + 120000:
                    long_asset = pos["long_asset"]
                    short_asset = pos["short_asset"]
                    l_price = live_data[long_asset]["price"]
                    s_price = live_data[short_asset]["price"]
                    
                    logger.info(f"⏳ 2-minute post-settlement boundary reached for {pos['pair_name']}! Market unwinding spread...")
                    self.close_pair_position(i, l_price, s_price)

        # 5. Tactical Auto-Trigger Opens (Enter exactly 5 minutes / 300 seconds before crossover)
        # Ensure we are not already holding the asset pair
        active_pairs = [p["pair_name"] for p in self.positions]
        
        for pair in DEFAULT_PAIRS:
            pair_name = pair["name"]
            l_asset = pair["long"]
            s_asset = pair["short"]
            
            if pair_name not in active_pairs and l_asset in live_data and s_asset in live_data:
                l_info = live_data[l_asset]
                s_info = live_data[s_asset]
                
                # Check Double-Yield condition: Long leg has negative funding AND Short leg has positive funding
                is_double_yield = l_info["rate"] < 0 and s_info["rate"] > 0
                combined_apr = s_info["apr"] - l_info["apr"]
                
                if is_double_yield and combined_apr >= self.min_apr_trigger:
                    # Check entry countdown: enter exactly 5 minutes (300 seconds) before crossover
                    countdown_sec = l_info["countdown_seconds"]
                    
                    if 0 < countdown_sec <= 300:
                        logger.info(f"💥 TACTICAL PAIR TRIGGERED! {pair_name} Combined APR: {combined_apr:.2f}% | Countdown: {countdown_sec:.0f}s <= 300s. Opening double-sided position...")
                        self.open_pair_position(
                            pair_name=pair_name,
                            long_asset=l_asset,
                            short_asset=s_asset,
                            long_rate=l_info["rate"],
                            short_rate=s_info["rate"],
                            long_apr=l_info["apr"],
                            short_apr=s_info["apr"],
                            long_price=l_info["price"],
                            short_price=s_info["price"],
                            funding_time_ms=l_info["funding_time_ms"]
                        )

def run_pair_funding_bot():
    logger.info("Initializing Live Tactical Pair Funding Arbitrage Daemon...")
    
    # Initialize public scans client
    public_exchange = None
    if ccxt:
        try:
            public_exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            public_exchange.load_markets()
            logger.info("Public CCXT Binance Swaps Scanner client active.")
        except Exception as e:
            logger.warning(f"Failed to connect public swaps scanner: {e}. Falling back to simulation.")
            public_exchange = None
            
    bot = PairFundingArbBot()
    bot.status = "running"
    bot.init_exchanges()
    bot.save_state()
    
    logger.info(f"Pair Funding bot successfully RUNNING | Leverage: {bot.futures_leverage}x | Open APR Trigger: {bot.min_apr_trigger}%")
    
    while True:
        # Check command loop state from state JSON
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("status") == "stopped":
                    logger.info("Halt command received. Safely stopping Pair Funding loop...")
                    break
            except Exception:
                pass
                
        try:
            bot.run_one_cycle(public_exchange)
            bot.save_state()
        except Exception as cycle_err:
            logger.error(f"❌ Error encountered in cycle: {cycle_err}")
            time.sleep(5.0)
            
        time.sleep(2.0) # Refresh scan every 2 seconds
        
    bot.status = "stopped"
    bot.save_state()
    logger.info("Pair Funding trading daemon safely stopped.")

if __name__ == "__main__":
    run_pair_funding_bot()
