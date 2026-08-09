# stockfish_basis_arb_bot.py
import os
import sys
import time
import json
import ccxt
import urllib.parse
import requests
import re
import traceback
from datetime import datetime, timezone, timedelta
try:
    import numpy as np
except ImportError:
    np = None

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

DEMO_API = "qsNKMuPZyeubUK7rpqligKksNO0tey"
DEMO_SECRET = "jjMmELW0NEENLvkHqVTCx6iQNJNzFI8EFeLkY7V7lb3NVfmteX4iOUE5ClNH"
ENDPOINT = "https://cdn-ind.testnet.deltaex.org"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "stockfish_basis_arb_state.json")
LOG_FILE = os.path.join(BASE_DIR, "stockfish_basis_arb.log")

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def sleep_checking_stop(seconds):
    steps = int(seconds / 0.5)
    for _ in range(steps):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    if not state.get("is_running", False):
                        return False
            except Exception:
                pass
        time.sleep(0.5)
    return True

def safe_amount_to_precision(exchange, symbol, amount):
    try:
        val = exchange.amount_to_precision(symbol, amount)
        if val is not None:
            return float(val)
    except Exception:
        pass
    
    if "BTC" in symbol:
        return round(amount, 4)
    elif "ETH" in symbol:
        return round(amount, 3)
    return round(amount, 2)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_message(f"Error loading state file: {e}")
    # Default State
    return {
        "is_running": False,
        "starting": False,
        "force_execute": False,
        "min_profit_pct": 1.0, # Stockfish score threshold trigger
        "trade_size_usd": 100.0,
        "leverage": 10,
        "accumulated_profit_usd": 0.0,
        "trades": [],
        "active_position": None,
        "last_update": datetime.now().isoformat()
    }

def save_state(state):
    state["last_update"] = datetime.now().isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        log_message(f"Error saving state file: {e}")

def spread_to_fen(spread_pct, funding_rate_apr, volatility_annual):
    board = [
        ["r", "n", "b", "q", "k", "b", "n", "r"],  # Rank 8
        ["p", "p", "p", "p", "p", "p", "p", "p"],  # Rank 7
        [".", ".", ".", ".", ".", ".", ".", "."],  # Rank 6
        [".", ".", ".", ".", ".", ".", ".", "."],  # Rank 5
        [".", ".", ".", ".", ".", ".", ".", "."],  # Rank 4
        [".", ".", ".", ".", ".", ".", ".", "."],  # Rank 3
        ["P", "P", "P", "P", "P", "P", "P", "P"],  # Rank 2
        ["R", "N", "B", "Q", "K", "B", "N", "R"]   # Rank 1
    ]
    
    # 1. Map Spread
    if spread_pct > 0.05:
        board[6][3] = "."
        board[6][4] = "."
        board[4][3] = "P"
        board[4][4] = "P"
        if spread_pct > 0.15:
            board[4][4] = "."
            board[3][4] = "P"
    elif spread_pct < -0.05:
        board[1][3] = "."
        board[1][4] = "."
        board[3][3] = "p"
        board[3][4] = "p"
        if spread_pct < -0.15:
            board[3][4] = "."
            board[4][4] = "p"
            
    # 2. Map Funding Rate
    if funding_rate_apr > 8.0:
        board[1][0] = "N"
    elif funding_rate_apr < -8.0:
        board[6][0] = "n"
        
    # 3. Map Volatility
    if volatility_annual > 0.40:
        board[7][4] = "."
        board[7][5] = "R"
        board[7][6] = "K"
        board[7][7] = "."
        board[0][4] = "."
        board[0][5] = "r"
        board[0][6] = "k"
        board[0][7] = "."
        for rank in range(1, 7):
            if board[rank][4] in ["P", "p"]:
                board[rank][4] = "."
                
    # FEN constructor
    fen_rows = []
    for row in board:
        empty_count = 0
        row_str = ""
        for cell in row:
            if cell == ".":
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += cell
        if empty_count > 0:
            row_str += str(empty_count)
        fen_rows.append(row_str)
        
    fen = "/".join(fen_rows)
    fen += " w KQkq - 0 1"
    return fen

def get_next_funding_datetime():
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    if hour < 8:
        target_hour = 8
        target_day = now_utc.day
        target_month = now_utc.month
        target_year = now_utc.year
    elif hour < 16:
        target_hour = 16
        target_day = now_utc.day
        target_month = now_utc.month
        target_year = now_utc.year
    else:
        tomorrow = now_utc + timedelta(days=1)
        target_hour = 0
        target_day = tomorrow.day
        target_month = tomorrow.month
        target_year = tomorrow.year
    return datetime(target_year, target_month, target_day, target_hour, 0, 0, tzinfo=timezone.utc)

def query_stockfish(fen):
    api_url = f"https://stockfish.online/api/s/v2.php?fen={urllib.parse.quote(fen)}&depth=10"
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                mate = res.get("mate")
                score = 99.0 if mate is not None and int(mate) > 0 else (-99.0 if mate is not None else float(res.get("evaluation", 0.0)))
                return True, score, mate, res.get("bestmove", "")
    except Exception:
        pass
    return False, 0.0, None, ""

def run_bot():
    state = load_state()
    state["pid"] = os.getpid()
    state["is_running"] = True
    state["starting"] = False
    save_state(state)
    
    log_message("==================================================")
    log_message(f"⚡ BOOTING STOCKFISH BASIS ARBITRAGE DAEMON (PID: {os.getpid()})")
    log_message("==================================================")
    
    exchange = ccxt.delta({
        'apiKey': DEMO_API,
        'secret': DEMO_SECRET,
        'enableRateLimit': True
    })
    exchange.urls['api'] = {
        'public': ENDPOINT,
        'private': ENDPOINT
    }
    
    try:
        exchange.load_markets()
        log_message("Exchange markets loaded successfully.")
        bal = exchange.fetch_balance()
        log_message(f"Connected to Delta Testnet. Wallet Margin: {bal.get('USD', {}).get('free', 0.0)} USD")
    except Exception as e:
        log_message(f"❌ [CRITICAL] Connection / Authentication failed: {e}")
        state = load_state()
        state["is_running"] = False
        state["pid"] = None
        save_state(state)
        sys.exit(1)
        
    loop_count = 0
    while True:
        try:
            state = load_state()
            if not state.get("is_running", False):
                log_message("Stop signal received in state. Exiting daemon loop.")
                break
                
            min_score = state.get("min_profit_pct", 1.0) # Using Stockfish threshold score
            trade_size = state.get("trade_size_usd", 100.0)
            lev = state.get("leverage", 10)
            active_pos = state.get("active_position")
            force_execute = state.get("force_execute", False)
            
            loop_count += 1
            if loop_count % 6 == 1:
                log_message(f"Heartbeat scan... Active Position: {active_pos is not None} | Thr: Score={min_score:.2f} | Leverage: {lev}x")
                
            # Fetch live prices (with spot fallback)
            tickers = exchange.fetch_tickers(['BTC/USDT', 'BTC/USD:USD'])
            t_spot = tickers.get('BTC/USDT')
            t_perp = tickers.get('BTC/USD:USD')
            
            spot_ask = t_spot.get('ask') if t_spot else None
            spot_bid = t_spot.get('bid') if t_spot else None
            perp_ask = t_perp.get('ask') if t_perp else None
            perp_bid = t_perp.get('bid') if t_perp else None
            
            if not spot_ask or not spot_bid:
                try:
                    binance = ccxt.binance()
                    bi_ticker = binance.fetch_ticker('BTC/USDT')
                    spot_ask = bi_ticker['ask']
                    spot_bid = bi_ticker['bid']
                except Exception:
                    pass
                    
            if not (spot_ask and spot_bid and perp_ask and perp_bid):
                log_message("⚠️ Market tickers fetch incomplete. Skipping cycle...")
                if not sleep_checking_stop(5):
                    break
                continue
                
            # Annualized funding rates
            funding_rate_apr = 12.0
            try:
                funding_info = exchange.fetch_funding_rate('BTC/USD:USD')
                funding_rate_apr = float(funding_info.get('fundingRate', 0.0001)) * 3 * 365 * 100.0
            except Exception:
                info = t_perp.get('info', {}) if t_perp else {}
                if 'funding_rate' in info:
                    funding_rate_apr = float(info['funding_rate']) * 3 * 365 * 100.0
                    
            # Basis volatility
            vol_annual = 0.45
            try:
                candles = exchange.fetch_ohlcv('BTC/USD:USD', timeframe='1h', limit=24)
                closes = [c[4] for c in candles]
                log_returns = np.diff(np.log(closes))
                vol_annual = np.std(log_returns) * np.sqrt(365 * 24)
                vol_annual = np.clip(vol_annual, 0.15, 1.20)
            except Exception:
                pass
                
            # Basis spread
            basis_spread_pct = ((perp_bid - spot_ask) / spot_ask) * 100.0
            
            # Translate to FEN board
            fen = spread_to_fen(basis_spread_pct, funding_rate_apr, vol_annual)
            
            # Consult Stockfish
            success, score, mate, bestmove = query_stockfish(fen)
            if not success:
                # Local Heuristic Fallback
                score = 1.2 if basis_spread_pct > 0.05 else (-1.2 if basis_spread_pct < -0.05 else 0.0)
                bestmove = "e2e4" if score >= 1.2 else "d2d4"
                
            # Update state variables for website display
            state = load_state()
            state["indicators"] = {
                "spot_ask": spot_ask,
                "spot_bid": spot_bid,
                "perp_ask": perp_ask,
                "perp_bid": perp_bid,
                "basis_spread_pct": basis_spread_pct,
                "funding_rate_apr": funding_rate_apr,
                "volatility_annual": vol_annual,
                "fen": fen,
                "score": score,
                "bestmove": bestmove
            }
            save_state(state)
            
            # POSITION LOGIC
            if active_pos is None:
                # Check for entry signal
                signal = None
                if score >= min_score or (force_execute and score >= 0):
                    signal = {
                        "direction": "SELL", # Short Perp, Buy Spot
                        "price": perp_bid,
                        "spot_price": spot_ask
                    }
                elif score <= -min_score or (force_execute and score < 0):
                    signal = {
                        "direction": "BUY", # Long Perp, Sell Spot
                        "price": perp_ask,
                        "spot_price": spot_bid
                    }
                    
                if signal:
                    log_message(f"🔥 Entry signal detected. Stockfish score: {score:+.2f} (Threshold: {min_score})")
                    # Calculate quantity contracts
                    # BTC contract size = 0.001
                    qty = trade_size / (0.001 * signal["price"])
                    qty_formatted = safe_amount_to_precision(exchange, "BTC/USD:USD", qty)
                    
                    is_sandbox = False
                    try:
                        log_message(f"Configuring perp leverage to {lev}x...")
                        exchange.set_leverage(lev, 'BTC/USD:USD')
                        
                        log_message(f"Placing perp trade: {signal['direction']} {qty_formatted} contracts...")
                        if signal["direction"] == "BUY":
                            order = exchange.create_market_buy_order('BTC/USD:USD', qty_formatted)
                        else:
                            order = exchange.create_market_sell_order('BTC/USD:USD', qty_formatted)
                        fill_price = order.get('average') or order.get('price') or signal["price"]
                        try:
                            fill_price = float(fill_price)
                        except (ValueError, TypeError):
                            fill_price = float(signal["price"])
                        log_message(f"  [SUCCESS] Order placed. ID: {order.get('id')} @ ${fill_price:,.2f}")
                    except Exception as ex:
                        log_message(f"  [ERROR] Live execution blocked: {ex}. Falling back to virtual sandbox.")
                        is_sandbox = True
                        fill_price = signal["price"]
                        
                    # Save position to state
                    state = load_state()
                    state["force_execute"] = False
                    next_funding_dt = get_next_funding_datetime()
                    next_funding_ts = next_funding_dt.timestamp()
                    next_funding_utc = next_funding_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    next_funding_ist = (next_funding_dt + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S IST")
                    
                    state["active_position"] = {
                        "symbol": "BTC/USD:USD",
                        "direction": signal["direction"],
                        "qty": qty_formatted,
                        "fill_price": fill_price,
                        "spot_price": signal["spot_price"],
                        "is_sandbox": is_sandbox,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "next_funding_timestamp": next_funding_ts,
                        "next_funding_time_utc": next_funding_utc,
                        "next_funding_time_ist": next_funding_ist
                    }
                    save_state(state)
                    
            else:
                # Check for exit signal
                # If we are Short Perp (direction = SELL), we close when Stockfish advantage drops below 0.5
                # If we are Long Perp (direction = BUY), we close when Stockfish advantage rises above -0.5
                unwind = False
                dir_side = active_pos["direction"]
                
                # Check if locked until next funding block passes
                now_ts = time.time()
                next_funding_ts = active_pos.get("next_funding_timestamp", 0)
                
                if now_ts < next_funding_ts + 15:
                    if loop_count % 6 == 1:
                        log_message(f"🔒 Position locked until funding block passes (Next funding: {active_pos.get('next_funding_time_ist', 'N/A')})")
                else:
                    if dir_side == "SELL" and score < 0.5:
                        unwind = True
                    elif dir_side == "BUY" and score > -0.5:
                        unwind = True
                    
                if unwind:
                    log_message(f"⚡ Exit signal detected. Stockfish score: {score:+.2f}. Closing position...")
                    
                    is_sandbox = active_pos.get("is_sandbox", True)
                    exit_price = perp_ask if dir_side == "SELL" else perp_bid
                    exit_spot = spot_bid if dir_side == "SELL" else spot_ask
                    
                    if not is_sandbox:
                        try:
                            log_message(f"Placing closing perp order: {'BUY' if dir_side == 'SELL' else 'SELL'} {active_pos['qty']} contracts...")
                            if dir_side == "SELL":
                                order = exchange.create_market_buy_order('BTC/USD:USD', active_pos['qty'])
                            else:
                                order = exchange.create_market_sell_order('BTC/USD:USD', active_pos['qty'])
                            exit_price = order.get('average') or order.get('price') or exit_price
                            try:
                                exit_price = float(exit_price)
                            except (ValueError, TypeError):
                                exit_price = float(exit_price)
                            log_message(f"  [SUCCESS] Closed order. ID: {order.get('id')} @ ${exit_price:,.2f}")
                        except Exception as ex:
                            log_message(f"  [ERROR] Live close execution failed: {ex}. Closing virtually in sandbox.")
                            
                    # Calculate Profit/Loss
                    # Short basis profit = (perp_sell - perp_buy) + (spot_sell - spot_buy)
                    if dir_side == "SELL":
                        perp_pnl = (active_pos["fill_price"] - exit_price) * 0.001 * active_pos["qty"]
                        spot_pnl = (exit_spot - active_pos["spot_price"]) * 0.001 * active_pos["qty"]
                    else:
                        perp_pnl = (exit_price - active_pos["fill_price"]) * 0.001 * active_pos["qty"]
                        spot_pnl = (active_pos["spot_price"] - exit_spot) * 0.001 * active_pos["qty"]
                        
                    # Fee deductions (0.1% spot, 0.05% perp for both entry & exit = 0.30% total)
                    nominal_val = active_pos["qty"] * 0.001 * active_pos["fill_price"]
                    fees = nominal_val * 0.003
                    net_profit = perp_pnl + spot_pnl - fees
                    
                    log_message(f"Trade Closed. PnL: Perp={perp_pnl:+.4f} | Spot={spot_pnl:+.4f} | Fees={fees:.4f} | Net={net_profit:+.4f} USD")
                    
                    # Record trade
                    trade_record = {
                        "timestamp_entry": active_pos["timestamp"],
                        "timestamp_exit": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "direction": active_pos["direction"],
                        "qty": active_pos["qty"],
                        "entry_perp": active_pos["fill_price"],
                        "exit_perp": exit_price,
                        "entry_spot": active_pos["spot_price"],
                        "exit_spot": exit_spot,
                        "fees_usd": fees,
                        "net_profit_usd": net_profit,
                        "is_sandbox": is_sandbox
                    }
                    
                    state = load_state()
                    state["trades"].append(trade_record)
                    state["accumulated_profit_usd"] += net_profit
                    state["active_position"] = None
                    save_state(state)
                    
            # Heartbeat sleep
            if not sleep_checking_stop(10):
                break
                
        except Exception as e:
            log_message(f"⚠️ Error in loop cycle: {e}")
            traceback.print_exc()
            if not sleep_checking_stop(10):
                break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--start", "--daemon"]:
        state = load_state()
        state["is_running"] = True
        save_state(state)
        
    state = load_state()
    if state.get("is_running", False):
        try:
            run_bot()
        except KeyboardInterrupt:
            log_message("Daemon stopped manually.")
        finally:
            state = load_state()
            state["is_running"] = False
            state["pid"] = None
            state["starting"] = False
            save_state(state)
            log_message("Daemon stopped.")
    else:
        log_message("is_running is False. Exiting.")
