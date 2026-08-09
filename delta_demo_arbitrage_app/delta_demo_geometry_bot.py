# delta_demo_geometry_bot.py
import os
import sys
import time
import json
import ccxt
import traceback
from datetime import datetime

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

DEMO_API = "J0qo3wjxK875fZzEfl02wAzZVF3AHa"
DEMO_SECRET = "UGtWmUs4wQITBHLsnVLffeKrnKLp8r15wcKZcH1GLwaIQsojJjvgWwK6BeR3"
ENDPOINT = "https://cdn-ind.testnet.deltaex.org"

# Resolve paths relative to this script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "delta_demo_geometry_state.json")
LOG_FILE = os.path.join(BASE_DIR, "delta_demo_geometry.log")

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    safe_formatted = "".join(c for c in formatted if ord(c) < 128 or c in ['📐', '📈', '🟢', '🔴', '🔥', '⚡', '🤖', '❌', '⚠️', '🏆', '✅', '⏰'])
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(safe_formatted + "\n")
    except Exception:
        pass

def sleep_checking_stop(seconds):
    GLOBAL_STATE_FILE = os.path.abspath(os.path.join(BASE_DIR, "../antigravity_ai_brain/ai_brain_state.json"))
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
        if os.path.exists(GLOBAL_STATE_FILE):
            try:
                with open(GLOBAL_STATE_FILE, "r", encoding="utf-8") as f:
                    g_state = json.load(f)
                    if not g_state.get("is_running", False):
                        return False
            except Exception:
                pass
        time.sleep(0.5)
    return True

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
        "pid": None,
        "trade_size_usd": 100.0,
        "target_profit_usd": 5.0, # Fixed gain to auto-unwind
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

def run_geometry():
    state = load_state()
    state["pid"] = os.getpid()
    state["is_running"] = True
    state["starting"] = False
    save_state(state)
    
    GLOBAL_STATE_FILE = os.path.abspath(os.path.join(BASE_DIR, "../antigravity_ai_brain/ai_brain_state.json"))
    if os.path.exists(GLOBAL_STATE_FILE):
        try:
            with open(GLOBAL_STATE_FILE, "r", encoding="utf-8") as f:
                g_state = json.load(f)
            g_state["pid"] = os.getpid()
            g_state["is_running"] = True
            g_state["starting"] = False
            g_state["last_update"] = datetime.now().isoformat()
            with open(GLOBAL_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(g_state, f, indent=4)
        except Exception as e:
            log_message(f"Error updating global state: {e}")

    log_message("==================================================")
    log_message(f"📐 BOOTING AI GEOMETRY DAEMON (DEEP ITM STRANGLE) (PID: {os.getpid()})")
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
        log_message("Loading exchange markets...")
        markets = exchange.load_markets()
        log_message(f"Markets loaded successfully. Total symbols: {len(exchange.symbols)}")
        
        bal = exchange.fetch_balance()
        log_message(f"Credentials authenticated successfully. USD Wallet Balance: {bal.get('USD', {}).get('free', 0.0)} USD")
    except Exception as e:
        log_message(f"❌ [CRITICAL ERROR] Connection Failed: {e}")
        state = load_state()
        state["is_running"] = False
        save_state(state)
        sys.exit(1)
        
    loop_count = 0
    while True:
        try:
            state = load_state()
            if not state.get("is_running", False):
                log_message("Stop signal received. Shutting down daemon.")
                break
                
            trade_size_usd = state.get("trade_size_usd", 100.0)
            target_profit_usd = state.get("target_profit_usd", 5.0)
            active_pos = state.get("active_position")
            
            loop_count += 1
            
            if not active_pos:
                # ---------------------------------------------------------
                # SCANNING MODE: Construct Deep ITM Strangle
                # ---------------------------------------------------------
                if loop_count % 6 == 1:
                    log_message(f"Scanning options chains for Deep ITM Strangle geometry... Target Size: ${trade_size_usd}")
                    
                btc_ticker = exchange.fetch_ticker('BTC/USD:USD')
                btc_price = btc_ticker.get('last', 60000)
                
                # Gather strikes for BTC options > 3 days expiry
                strikes_by_expiry = {}
                for symbol, m in markets.items():
                    if m.get('option') and m.get('base') == 'BTC':
                        expiry = m.get('expiryDatetime')
                        strike = m.get('strike')
                        opt_type = m.get('optionType')
                        if expiry and strike and opt_type:
                            exp_dt = datetime.strptime(expiry.split('T')[0], "%Y-%m-%d")
                            days_to_expiry = (exp_dt - datetime.today()).days
                            if 3 < days_to_expiry < 45: # Looking for 3 to 45 days
                                if expiry not in strikes_by_expiry:
                                    strikes_by_expiry[expiry] = {'calls': [], 'puts': []}
                                if opt_type.lower() == 'call':
                                    strikes_by_expiry[expiry]['calls'].append((strike, symbol))
                                elif opt_type.lower() == 'put':
                                    strikes_by_expiry[expiry]['puts'].append((strike, symbol))
                                    
                if strikes_by_expiry:
                    # Pick the expiry with the most strikes
                    best_expiry = max(strikes_by_expiry.keys(), key=lambda k: len(strikes_by_expiry[k]['calls']))
                    calls = sorted(strikes_by_expiry[best_expiry]['calls'], key=lambda x: x[0])
                    puts = sorted(strikes_by_expiry[best_expiry]['puts'], key=lambda x: x[0])
                    
                    if calls and puts:
                        # Deepest ITM Call = Lowest Strike (must have real ask)
                        call_symbol = None
                        lowest_call_strike = None
                        c_ask = None
                        for strike, sym in calls:
                            t = exchange.fetch_ticker(sym)
                            ask = t.get('ask')
                            if ask:
                                call_symbol = sym
                                lowest_call_strike = strike
                                c_ask = ask
                                break

                        # Deepest ITM Put = Highest strike that has a REAL ask price
                        put_symbol = None
                        highest_put_strike = None
                        p_ask = None
                        for strike, sym in reversed(puts):  # highest strike first
                            t = exchange.fetch_ticker(sym)
                            ask = t.get('ask')
                            if ask:
                                put_symbol = sym
                                highest_put_strike = strike
                                p_ask = ask
                                break

                        if c_ask and p_ask:
                            log_message(f"🔥 GEOMETRY FOUND! Expiry: {best_expiry.split('T')[0]}")
                            log_message(f"  Deep ITM Call: Strike ${lowest_call_strike} ({call_symbol}) - Ref Price: ${c_ask:.2f}")
                            log_message(f"  Deep ITM Put:  Strike ${highest_put_strike} ({put_symbol}) - Ref Price: ${p_ask:.2f}")
                            
                            # Calculate quantities for fixed USD exposure per leg
                            leg_size_usd = trade_size_usd / 2.0
                            market_c = markets.get(call_symbol)
                            contract_size = market_c.get('contractSize') or 0.001
                            
                            qty_call = round(leg_size_usd / (c_ask * contract_size))
                            qty_put = round(leg_size_usd / (p_ask * contract_size))
                            if qty_call < 1: qty_call = 1
                            if qty_put < 1: qty_put = 1
                            
                            log_message(f"Placing orders: Buy {qty_call}x Call @ ~${c_ask:.2f}, Buy {qty_put}x Put @ ~${p_ask:.2f}...")
                            
                            try:
                                # Try market order first; fallback to aggressive limit if market fails
                                try:
                                    o_call = exchange.create_market_buy_order(call_symbol, qty_call)
                                except Exception:
                                    limit_c = round(c_ask * 1.05, 1)  # 5% above reference to ensure fill
                                    o_call = exchange.create_limit_buy_order(call_symbol, qty_call, limit_c)
                                    log_message(f"  Call: market failed, placed limit @ ${limit_c}")
                                
                                try:
                                    o_put = exchange.create_market_buy_order(put_symbol, qty_put)
                                except Exception:
                                    limit_p = round(p_ask * 1.05, 1)
                                    o_put = exchange.create_limit_buy_order(put_symbol, qty_put, limit_p)
                                    log_message(f"  Put: market failed, placed limit @ ${limit_p}")
                                
                                c_fill = float(o_call.get('average') or o_call.get('price') or c_ask)
                                p_fill = float(o_put.get('average') or o_put.get('price') or p_ask)
                                
                                total_cost = (c_fill * qty_call * contract_size) + (p_fill * qty_put * contract_size)
                                log_message(f"✅ Deep ITM Strangle Constructed! Total Premium Cost: ${total_cost:.2f} USD")
                                
                                state["active_position"] = {
                                    "geometry": "Deep_ITM_Strangle",
                                    "expiry": best_expiry,
                                    "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "total_cost": total_cost,
                                    "contract_size": contract_size,
                                    "call": {
                                        "symbol": call_symbol,
                                        "qty": qty_call,
                                        "entry_price": c_fill,
                                        "strike": lowest_call_strike
                                    },
                                    "put": {
                                        "symbol": put_symbol,
                                        "qty": qty_put,
                                        "entry_price": p_fill,
                                        "strike": highest_put_strike
                                    }
                                }
                                save_state(state)
                            except Exception as ex:
                                log_message(f"❌ Error constructing geometry: {ex}")
                        else:
                            log_message(f"⚠️ No valid price found for both legs. Call ref: {c_ask}, Put ref: {p_ask}. Waiting...")
                                
                if not sleep_checking_stop(15):
                    break

                    
            else:
                # ---------------------------------------------------------
                # MONITORING MODE: Wait for Fixed Gain
                # ---------------------------------------------------------
                c_symbol = active_pos["call"]["symbol"]
                p_symbol = active_pos["put"]["symbol"]
                c_qty = active_pos["call"]["qty"]
                p_qty = active_pos["put"]["qty"]
                c_entry = active_pos["call"]["entry_price"]
                p_entry = active_pos["put"]["entry_price"]
                contract_size = active_pos["contract_size"]
                total_cost = active_pos["total_cost"]
                
                c_ticker = exchange.fetch_ticker(c_symbol)
                p_ticker = exchange.fetch_ticker(p_symbol)
                
                # We need bids to sell our long options
                c_bid = c_ticker.get('bid')
                p_bid = p_ticker.get('bid')
                
                if c_bid and p_bid:
                    current_call_value = c_bid * c_qty * contract_size
                    current_put_value = p_bid * p_qty * contract_size
                    current_total_value = current_call_value + current_put_value
                    
                    net_pnl = current_total_value - total_cost
                    
                    # Store current unrealized for frontend
                    state["active_position"]["current_call_price"] = c_bid
                    state["active_position"]["current_put_price"] = p_bid
                    state["active_position"]["unrealized_pnl"] = net_pnl
                    save_state(state)
                    
                    if loop_count % 6 == 1:
                        log_message(f"Monitoring Geometry | C-Bid: ${c_bid:.2f} | P-Bid: ${p_bid:.2f} | Net PnL: ${net_pnl:+.4f} USD (Target: +${target_profit_usd})")
                    
                    # Auto unwind if fixed gain is hit
                    if net_pnl >= target_profit_usd:
                        log_message(f"🏆 FIXED GAIN TARGET HIT! Net PnL ${net_pnl:+.4f} >= ${target_profit_usd}. Unwinding geometry...")
                        
                        try:
                            # Close longs by selling them
                            o_c_close = exchange.create_market_sell_order(c_symbol, c_qty, params={'reduceOnly': True})
                            o_p_close = exchange.create_market_sell_order(p_symbol, p_qty, params={'reduceOnly': True})
                            
                            c_exit = float(o_c_close.get('average', c_bid))
                            p_exit = float(o_p_close.get('average', p_bid))
                            
                            real_val = (c_exit * c_qty * contract_size) + (p_exit * p_qty * contract_size)
                            real_pnl = real_val - total_cost
                            
                            log_message(f"✅ Geometry Unwound Successfully! Realized PnL: ${real_pnl:+.4f} USD")
                            
                            trade_record = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "geometry": "Deep_ITM_Strangle",
                                "net_pnl": real_pnl,
                                "call_exit": c_exit,
                                "put_exit": p_exit
                            }
                            
                            state["active_position"] = None
                            state["trades"].append(trade_record)
                            state["accumulated_profit_usd"] += real_pnl
                            save_state(state)
                            
                        except Exception as e:
                            log_message(f"❌ Error unwinding geometry: {e}")
                
                if not sleep_checking_stop(10):
                    break

        except Exception as loop_ex:
            log_message(f"⚠️ Error in daemon cycle: {loop_ex}")
            traceback.print_exc()
            if not sleep_checking_stop(5):
                break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--start", "--daemon"]:
        state = load_state()
        state["is_running"] = True
        save_state(state)
        
    state = load_state()
    if state.get("is_running", False):
        try:
            run_geometry()
        except KeyboardInterrupt:
            log_message("Geometry Daemon stopped manually.")
        finally:
            state = load_state()
            state["is_running"] = False
            state["pid"] = None
            state["starting"] = False
            save_state(state)
            
            GLOBAL_STATE_FILE = os.path.abspath(os.path.join(BASE_DIR, "../antigravity_ai_brain/ai_brain_state.json"))
            if os.path.exists(GLOBAL_STATE_FILE):
                try:
                    with open(GLOBAL_STATE_FILE, "r", encoding="utf-8") as f:
                        g_state = json.load(f)
                    g_state["is_running"] = False
                    g_state["pid"] = None
                    g_state["starting"] = False
                    g_state["last_update"] = datetime.now().isoformat()
                    with open(GLOBAL_STATE_FILE, "w", encoding="utf-8") as f:
                        json.dump(g_state, f, indent=4)
                except Exception as e:
                    log_message(f"Error clearing global state: {e}")
            log_message("Geometry Daemon stopped.")
    else:
        log_message("is_running is False in state. Geometry Daemon will not run.")
