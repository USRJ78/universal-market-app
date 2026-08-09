# delta_demo_golden_straddle_bot.py
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

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "delta_demo_golden_straddle_state.json")
LOG_FILE = os.path.join(BASE_DIR, "delta_demo_golden_straddle.log")

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
        "target_profit_usd": 3.0,
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

def run_golden_straddle():
    state = load_state()
    state["pid"] = os.getpid()
    state["is_running"] = True
    state["starting"] = False
    save_state(state)

    log_message("==================================================")
    log_message(f"📐 BOOTING GOLDEN STRADDLE + FIB HEDGE BOT (PID: {os.getpid()})")
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
        log_message(f"Markets loaded. Total symbols: {len(exchange.symbols)}")
    except Exception as e:
        log_message(f"Error starting CCXT: {e}")
        return

    loop_count = 0
    target_profit_usd = state.get("target_profit_usd", 3.0)

    while True:
        try:
            loop_count += 1
            state = load_state()
            if not state.get("is_running", False):
                log_message("Stop signal detected in state. Exiting...")
                break

            active_pos = state.get("active_position")

            if not active_pos:
                # ---------------------------------------------------------
                # SCANNING MODE: Construct Golden Straddle + Fib Hedge
                # ---------------------------------------------------------
                if loop_count % 6 == 1:
                    log_message("Scanning options chains for Golden Straddle + Fib Hedge...")

                tickers = exchange.fetch_tickers()
                btc_price = tickers.get('BTC/USD:USD', {}).get('last')
                if not btc_price:
                    log_message("Could not fetch BTC spot price. Retrying...")
                    if not sleep_checking_stop(15): break
                    continue

                # Group by expiry
                options_by_expiry = {}
                for symbol, m in markets.items():
                    if m.get('option') and m.get('base') == 'BTC':
                        expiry = m.get('expiryDatetime')
                        strike = m.get('strike')
                        opt_type = m.get('optionType')
                        if expiry and strike and opt_type:
                            exp_dt = datetime.strptime(expiry.split('T')[0], "%Y-%m-%d")
                            days = (exp_dt - datetime.today()).days
                            if days > 1:
                                if expiry not in options_by_expiry:
                                    options_by_expiry[expiry] = {'calls': [], 'puts': [], 'days': days}
                                if opt_type.lower() == 'call':
                                    options_by_expiry[expiry]['calls'].append((strike, symbol))
                                elif opt_type.lower() == 'put':
                                    options_by_expiry[expiry]['puts'].append((strike, symbol))

                if not options_by_expiry:
                    log_message("No option chains found.")
                    if not sleep_checking_stop(15): break
                    continue

                # Find expiry closest to 14 days and expiry closest to 30 days
                expiries = list(options_by_expiry.keys())
                expiry_14 = min(expiries, key=lambda k: abs(options_by_expiry[k]['days'] - 14))
                expiry_30 = min(expiries, key=lambda k: abs(options_by_expiry[k]['days'] - 30))

                days_14 = options_by_expiry[expiry_14]['days']
                days_30 = options_by_expiry[expiry_30]['days']

                if expiry_14 == expiry_30:
                    log_message(f"Warning: Closest 14d and 30d expiries mapped to the same date ({expiry_14}). Waiting for better term structure...")
                    if not sleep_checking_stop(15): break
                    continue

                # 1. ATM Long legs (14d)
                calls_14 = sorted(options_by_expiry[expiry_14]['calls'], key=lambda x: abs(x[0] - btc_price))
                puts_14  = sorted(options_by_expiry[expiry_14]['puts'], key=lambda x: abs(x[0] - btc_price))

                # 2. OTM Short legs (30d)
                target_call_strike = btc_price * 1.162
                target_put_strike  = btc_price * 0.838

                calls_30 = sorted(options_by_expiry[expiry_30]['calls'], key=lambda x: abs(x[0] - target_call_strike))
                puts_30  = sorted(options_by_expiry[expiry_30]['puts'], key=lambda x: abs(x[0] - target_put_strike))

                if calls_14 and puts_14 and calls_30 and puts_30:
                    long_call_strike, long_call_sym = calls_14[0]
                    long_put_strike,  long_put_sym  = puts_14[0]
                    short_call_strike, short_call_sym = calls_30[0]
                    short_put_strike,  short_put_sym  = puts_30[0]

                    # Fetch pricing
                    lc_ask = tickers.get(long_call_sym, {}).get('ask')
                    lp_ask = tickers.get(long_put_sym, {}).get('ask')
                    sc_bid = tickers.get(short_call_sym, {}).get('bid')
                    sp_bid = tickers.get(short_put_sym, {}).get('bid')

                    if all([lc_ask, lp_ask, sc_bid, sp_bid]):
                        log_message("🔥 GEOMETRY TARGETS IDENTIFIED:")
                        log_message(f"  Long Legs (14d - Expiry: {expiry_14.split('T')[0]}, {days_14} days):")
                        log_message(f"    - CALL Strike ${long_call_strike} ({long_call_sym}) - Ask: ${lc_ask:.2f}")
                        log_message(f"    - PUT  Strike ${long_put_strike} ({long_put_sym}) - Ask: ${lp_ask:.2f}")
                        log_message(f"  Short Legs (30d - Expiry: {expiry_30.split('T')[0]}, {days_30} days):")
                        log_message(f"    - CALL Strike ${short_call_strike} ({short_call_sym}) - Bid: ${sc_bid:.2f}")
                        log_message(f"    - PUT  Strike ${short_put_strike} ({short_put_sym}) - Bid: ${sp_bid:.2f}")

                        # Sizing: Long Straddle = 2 contracts, Short Hedge = 1 contract
                        qty_long = 2
                        qty_short = 1

                        c_size = markets.get(long_call_sym, {}).get('contractSize') or 0.001

                        net_premium_debit = (lc_ask * qty_long * c_size) + (lp_ask * qty_long * c_size) - \
                                            (sc_bid * qty_short * c_size) - (sp_bid * qty_short * c_size)

                        log_message(f"Estimated Net Premium Debit: ${net_premium_debit:.2f} USD")
                        log_message("Executing market orders...")

                        try:
                            # 1. Place buy orders
                            o_lc = exchange.create_market_buy_order(long_call_sym, qty_long)
                            o_lp = exchange.create_market_buy_order(long_put_sym, qty_long)
                            # 2. Place sell orders
                            o_sc = exchange.create_market_sell_order(short_call_sym, qty_short)
                            o_sp = exchange.create_market_sell_order(short_put_sym, qty_short)

                            lc_fill = float(o_lc.get('average', lc_ask))
                            lp_fill = float(o_lp.get('average', lp_ask))
                            sc_fill = float(o_sc.get('average', sc_bid))
                            sp_fill = float(o_sp.get('average', sp_bid))

                            real_debit = (lc_fill * qty_long * c_size) + (lp_fill * qty_long * c_size) - \
                                         (sc_fill * qty_short * c_size) - (sp_fill * qty_short * c_size)

                            log_message(f"✅ Golden Straddle constructed! Realized net debit: ${real_debit:.2f} USD")

                            state["active_position"] = {
                                "geometry": "Golden_Straddle_Fib_Hedge",
                                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "net_premium_cost": real_debit,
                                "contract_size": c_size,
                                "expiry_long": expiry_14,
                                "expiry_short": expiry_30,
                                "call_long": {"symbol": long_call_sym, "qty": qty_long, "entry_price": lc_fill, "strike": long_call_strike},
                                "put_long": {"symbol": long_put_sym, "qty": qty_long, "entry_price": lp_fill, "strike": long_put_strike},
                                "call_short": {"symbol": short_call_sym, "qty": qty_short, "entry_price": sc_fill, "strike": short_call_strike},
                                "put_short": {"symbol": short_put_sym, "qty": qty_short, "entry_price": sp_fill, "strike": short_put_strike}
                            }
                            save_state(state)

                        except Exception as o_err:
                            log_message(f"❌ Error placing setup orders: {o_err}")

                if not sleep_checking_stop(15): break

            else:
                # ---------------------------------------------------------
                # MONITORING MODE: Wait for targets or expiry
                # ---------------------------------------------------------
                lc_symbol = active_pos["call_long"]["symbol"]
                lp_symbol = active_pos["put_long"]["symbol"]
                sc_symbol = active_pos["call_short"]["symbol"]
                sp_symbol = active_pos["put_short"]["symbol"]

                lc_qty = active_pos["call_long"]["qty"]
                lp_qty = active_pos["put_long"]["qty"]
                sc_qty = active_pos["call_short"]["qty"]
                sp_qty = active_pos["put_short"]["qty"]

                lc_entry = active_pos["call_long"]["entry_price"]
                lp_entry = active_pos["put_long"]["entry_price"]
                sc_entry = active_pos["call_short"]["entry_price"]
                sp_entry = active_pos["put_short"]["entry_price"]

                c_size = active_pos["contract_size"]
                net_premium_cost = active_pos["net_premium_cost"]

                # Fetch live tickers
                tickers = exchange.fetch_tickers()
                lc_bid = tickers.get(lc_symbol, {}).get('bid')
                lp_bid = tickers.get(lp_symbol, {}).get('bid')
                sc_ask = tickers.get(sc_symbol, {}).get('ask')
                sp_ask = tickers.get(sp_symbol, {}).get('ask')

                if all([lc_bid, lp_bid, sc_ask, sp_ask]):
                    # Value long legs (exit via sell => bids)
                    val_lc = lc_bid * lc_qty * c_size
                    val_lp = lp_bid * lp_qty * c_size

                    # Value short legs (exit via buyback => asks)
                    val_sc = sc_ask * sc_qty * c_size
                    val_sp = sp_ask * sp_qty * c_size

                    # Net liquidation value of entire setup
                    net_liq_value = (val_lc + val_lp) - (val_sc + val_sp)
                    net_pnl = net_liq_value - net_premium_cost

                    # Update state
                    state["active_position"]["call_long"]["current_price"] = lc_bid
                    state["active_position"]["put_long"]["current_price"] = lp_bid
                    state["active_position"]["call_short"]["current_price"] = sc_ask
                    state["active_position"]["put_short"]["current_price"] = sp_ask
                    state["active_position"]["unrealized_pnl"] = net_pnl
                    save_state(state)

                    if loop_count % 6 == 1:
                        log_message(f"Monitoring | LC-Bid: ${lc_bid:.2f} | LP-Bid: ${lp_bid:.2f} | SC-Ask: ${sc_ask:.2f} | SP-Ask: ${sp_ask:.2f} | Net PnL: ${net_pnl:+.4f} USD (Target: +${target_profit_usd})")

                    # Exit condition
                    if net_pnl >= target_profit_usd:
                        log_message(f"🏆 TARGET HIT! Net PnL ${net_pnl:+.4f} >= ${target_profit_usd}. Unwinding...")

                        try:
                            # 1. Close longs (Sell)
                            o_lc_exit = exchange.create_market_sell_order(lc_symbol, lc_qty, params={'reduceOnly': True})
                            o_lp_exit = exchange.create_market_sell_order(lp_symbol, lp_qty, params={'reduceOnly': True})
                            # 2. Close shorts (Buy)
                            o_sc_exit = exchange.create_market_buy_order(sc_symbol, sc_qty, params={'reduceOnly': True})
                            o_sp_exit = exchange.create_market_buy_order(sp_symbol, sp_qty, params={'reduceOnly': True})

                            lc_exit = float(o_lc_exit.get('average', lc_bid))
                            lp_exit = float(o_lp_exit.get('average', lp_bid))
                            sc_exit = float(o_sc_exit.get('average', sc_ask))
                            sp_exit = float(o_sp_exit.get('average', sp_ask))

                            real_exit_val = (lc_exit * lc_qty * c_size) + (lp_exit * lp_qty * c_size) - \
                                            (sc_exit * sc_qty * c_size) - (sp_exit * sp_qty * c_size)
                            real_pnl = real_exit_val - net_premium_cost

                            log_message(f"✅ Golden Straddle Unwound! Realized PnL: ${real_pnl:+.4f} USD")

                            trade_record = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "geometry": "Golden_Straddle_Fib_Hedge",
                                "net_pnl": real_pnl,
                                "details": {
                                    "lc_exit": lc_exit, "lp_exit": lp_exit,
                                    "sc_exit": sc_exit, "sp_exit": sp_exit
                                }
                            }
                            state["active_position"] = None
                            state["trades"].append(trade_record)
                            state["accumulated_profit_usd"] += real_pnl
                            save_state(state)

                        except Exception as e:
                            log_message(f"❌ Error during unwind execution: {e}")

                if not sleep_checking_stop(10): break

        except Exception as loop_ex:
            log_message(f"⚠️ Error in daemon loop: {loop_ex}")
            traceback.print_exc()
            if not sleep_checking_stop(5): break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--start", "--daemon"]:
        state = load_state()
        state["is_running"] = True
        save_state(state)

    state = load_state()
    if state.get("is_running", False):
        try:
            run_golden_straddle()
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
        log_message("is_running is False. Golden Straddle bot will not start.")
