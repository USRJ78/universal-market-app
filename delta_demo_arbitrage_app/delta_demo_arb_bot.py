# delta_demo_arb_bot.py
import os
import sys
import time
import json
import ccxt
import traceback
from datetime import datetime

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

DEMO_API = "qsNKMuPZyeubUK7rpqligKksNO0tey"
DEMO_SECRET = "jjMmELW0NEENLvkHqVTCx6iQNJNzFI8EFeLkY7V7lb3NVfmteX4iOUE5ClNH"
ENDPOINT = "https://cdn-ind.testnet.deltaex.org"

# Resolve paths relative to this script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "delta_demo_arb_state.json")
LOG_FILE = os.path.join(BASE_DIR, "delta_demo_arb.log")

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def sleep_checking_stop(seconds):
    steps = int(seconds / 0.5)
    for _ in range(steps):
        # We read the file directly to bypass any thread cache issues
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
    
    try:
        market = exchange.market(symbol)
        precision = market.get('precision', {})
        amount_prec = precision.get('amount')
        if amount_prec is not None:
            if isinstance(amount_prec, int):
                return round(amount, amount_prec)
            elif isinstance(amount_prec, float):
                import decimal
                dec = abs(decimal.Decimal(str(amount_prec)).as_tuple().exponent)
                return round(amount, dec)
    except Exception:
        pass
        
    if "BTC" in symbol:
        return round(amount, 4)
    elif "ETH" in symbol:
        return round(amount, 3)
    else:
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
        "force_execute": False,
        "min_profit_pct": 0.15,
        "trade_size_usd": 100.0,
        "leverage": 20,
        "accumulated_profit_usd": 0.0,
        "trades": [],
        "last_update": datetime.now().isoformat()
    }

def save_state(state):
    state["last_update"] = datetime.now().isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        log_message(f"Error saving state file: {e}")

def run_arbitrage():
    # Save PID and set running state
    state = load_state()
    state["pid"] = os.getpid()
    state["is_running"] = True
    state["starting"] = False
    save_state(state)

    log_message("==================================================")
    log_message(f"⚡ BOOTING DELTA EXCHANGE DEMO ARBITRAGE DAEMON (PID: {os.getpid()})")
    log_message("==================================================")
    log_message(f"Target API Endpoint: {ENDPOINT}")
    
    # Initialize CCXT exchange client
    exchange = ccxt.delta({
        'apiKey': DEMO_API,
        'secret': DEMO_SECRET,
        'enableRateLimit': True
    })
    exchange.urls['api'] = {
        'public': ENDPOINT,
        'private': ENDPOINT
    }
    
    # Try to load markets and test credentials
    try:
        log_message("Loading exchange markets...")
        exchange.load_markets()
        log_message(f"Markets loaded successfully. Total symbols: {len(exchange.symbols)}")
        
        log_message("Verifying API credentials balance...")
        bal = exchange.fetch_balance()
        log_message(f"Credentials authenticated successfully. USDT Wallet Balance: {bal.get('USDT', {}).get('free', 0.0)} USDT")
    except Exception as e:
        err_str = str(e).lower()
        log_message("❌ [CRITICAL ERROR] Authentication / Connection Failed!")
        if "ip_not_whitelisted" in err_str or "ip_not_whitelisted_for_api_key" in err_str:
            # Try to parse client IP
            import re
            ip_match = re.search(r'"client_ip"\s*:\s*"([^"]+)"', str(e))
            client_ip = ip_match.group(1) if ip_match else "your IP address"
            log_message(f"❌ REASON: IP address {client_ip} is not whitelisted in Delta API settings.")
        else:
            log_message(f"❌ REASON: {e}")
        
        # Shutdown bot in state
        state = load_state()
        state["is_running"] = False
        save_state(state)
        log_message("Daemon shutting down.")
        sys.exit(1)
        
    loop_count = 0
    while True:
        try:
            # Load state to check if user turned off the daemon
            state = load_state()
            if not state.get("is_running", False):
                log_message("Stop signal received in state. Shutting down daemon loop.")
                break
            min_profit = state.get("min_profit_pct", 0.15) / 100.0
            trade_size = state.get("trade_size_usd", 100.0)
            force_execute = state.get("force_execute", False)
            
            loop_count += 1
            if loop_count % 12 == 1: # Log heartbeat every 60 seconds (12 * 5s)
                log_message(f"Heartbeat: scanning markets... Min Profit Trigger: {min_profit*100:.3f}%, Size: ${trade_size:.2f}")
                
            # Fetch tickers for the 4 legs
            tickers = exchange.fetch_tickers(['BTC/USDT', 'ETH/USDT', 'BTC/USD:USD', 'ETH/USD:USD'])
            
            ticker_spot_btc = tickers.get('BTC/USDT')
            ticker_spot_eth = tickers.get('ETH/USDT')
            ticker_perp_btc = tickers.get('BTC/USD:USD')
            ticker_perp_eth = tickers.get('ETH/USD:USD')
            
            if not (ticker_spot_btc and ticker_spot_eth and ticker_perp_btc and ticker_perp_eth):
                log_message("⚠️ Incomplete tickers fetched. Skipping cycle...")
                if not sleep_checking_stop(5):
                    break
                continue
                
            # Prices
            spot_btc_ask = ticker_spot_btc.get('ask')
            perp_btc_bid = ticker_perp_btc.get('bid')
            perp_eth_ask = ticker_perp_eth.get('ask')
            spot_eth_bid = ticker_spot_eth.get('bid')
            
            spot_eth_ask = ticker_spot_eth.get('ask')
            perp_eth_bid = ticker_perp_eth.get('bid')
            perp_btc_ask = ticker_perp_btc.get('ask')
            spot_btc_bid = ticker_spot_btc.get('bid')
            
            # Fallback spot prices from Binance public API if testnet spot is inactive
            if not spot_btc_ask or not spot_btc_bid or not spot_eth_ask or not spot_eth_bid:
                try:
                    binance = ccxt.binance({'enableRateLimit': True})
                    bi_tickers = binance.fetch_tickers(['BTC/USDT', 'ETH/USDT'])
                    
                    if not spot_btc_ask or not spot_btc_bid:
                        spot_btc_ask = bi_tickers['BTC/USDT']['ask'] or bi_tickers['BTC/USDT']['last']
                        spot_btc_bid = bi_tickers['BTC/USDT']['bid'] or bi_tickers['BTC/USDT']['last']
                    if not spot_eth_ask or not spot_eth_bid:
                        spot_eth_ask = bi_tickers['ETH/USDT']['ask'] or bi_tickers['ETH/USDT']['last']
                        spot_eth_bid = bi_tickers['ETH/USDT']['bid'] or bi_tickers['ETH/USDT']['last']
                except Exception as ex:
                    log_message(f"⚠️ Spot prices fallback failed: {ex}")
                    
            if not (spot_btc_ask and perp_btc_bid and perp_eth_ask and spot_eth_bid and
                    spot_eth_ask and perp_eth_bid and perp_btc_ask and spot_btc_bid):
                log_message("⚠️ Zero/Null prices detected. Skipping cycle...")
                if not sleep_checking_stop(5):
                    break
                continue
                
            # Calculate return (Taker fees: 0.1% spot, 0.05% futures swap = approx 0.3% total cost)
            est_fees_pct = 0.003
            
            # Spread A Return
            ret_A = (perp_btc_bid / spot_btc_ask) * (spot_eth_bid / perp_eth_ask) - 1.0
            net_ret_A = ret_A - est_fees_pct
            
            # Spread B Return
            ret_B = (perp_eth_bid / spot_eth_ask) * (spot_btc_bid / perp_btc_ask) - 1.0
            net_ret_B = ret_B - est_fees_pct
            
            # Check spreads
            opportunity = None
            if net_ret_A > min_profit or (force_execute and net_ret_A >= net_ret_B):
                opportunity = {
                    "direction": "SPOT_BTC_TO_PERP_ETH",
                    "net_return": net_ret_A,
                    "legs": {
                        "L1_SpotBuyBTC": ("BTC/USDT", "BUY", spot_btc_ask, True),
                        "L2_PerpShortBTC": ("BTC/USD:USD", "SELL", perp_btc_bid, False),
                        "L3_PerpLongETH": ("ETH/USD:USD", "BUY", perp_eth_ask, False),
                        "L4_SpotSellETH": ("ETH/USDT", "SELL", spot_eth_bid, True)
                    }
                }
            elif net_ret_B > min_profit or (force_execute and net_ret_B > net_ret_A):
                opportunity = {
                    "direction": "SPOT_ETH_TO_PERP_BTC",
                    "net_return": net_ret_B,
                    "legs": {
                        "L1_SpotBuyETH": ("ETH/USDT", "BUY", spot_eth_ask, True),
                        "L2_PerpShortETH": ("ETH/USD:USD", "SELL", perp_eth_bid, False),
                        "L3_PerpLongBTC": ("BTC/USD:USD", "BUY", perp_btc_ask, False),
                        "L4_SpotSellBTC": ("BTC/USDT", "SELL", spot_btc_bid, True)
                    }
                }
                
            if opportunity:
                if force_execute:
                    log_message(f"⚡ [FORCE EXECUTE ACTIVATED] Net Spread: {opportunity['net_return']*100:.3f}% (Bypassing threshold: {min_profit*100:.3f}%)")
                else:
                    log_message(f"🔥 OPPORTUNITY DETECTED! Net Spread: {opportunity['net_return']*100:.3f}% (Target: {min_profit*100:.3f}%)")
                log_message(f"Direction: {opportunity['direction']}")
                
                # Execute orders sequentially (real perp execution, simulated spot fills)
                log_message("Initiating sequential order execution...")
                order_results = []
                success = True
                
                try:
                    for leg_name, (symbol, side, price, is_simulated) in opportunity["legs"].items():
                        market = exchange.market(symbol)
                        contract_size = market.get('contractSize')
                        is_perp = market.get('linear') or market.get('inverse') or (contract_size is not None and contract_size != 1.0)
                        
                        # Sizing based on contract vs asset units
                        if is_perp and contract_size is not None:
                            qty = trade_size / (contract_size * price)
                        else:
                            qty = trade_size / price
                            
                        qty_formatted = safe_amount_to_precision(exchange, symbol, qty)
                        
                        if is_simulated:
                            log_message(f"Simulating {side} Spot order for {qty_formatted} {symbol} at target ${price} (empty testnet spot book)...")
                            mock_order = {
                                "id": f"sim_spot_{int(time.time()*1000)}",
                                "symbol": symbol,
                                "side": side.lower(),
                                "amount": qty_formatted,
                                "price": price,
                                "average": price,
                                "status": "closed"
                            }
                            order_results.append(mock_order)
                        else:
                            # Configure contract leverage dynamically before order placement
                            try:
                                lev = state.get("leverage", 20)
                                log_message(f"Configuring leverage to {lev}x for {symbol} perp...")
                                exchange.set_leverage(lev, symbol)
                            except Exception as lev_ex:
                                log_message(f"⚠️ Warning setting leverage: {lev_ex}")

                            log_message(f"Placing REAL {side} Perp order for {qty_formatted} {symbol} at target ${price}...")
                            if side == "BUY":
                                order = exchange.create_market_buy_order(symbol, qty_formatted)
                            else:
                                order = exchange.create_market_sell_order(symbol, qty_formatted)
                            log_message(f"  [SUCCESS] Real Order Placed! Order ID: {order.get('id')}")
                            order_results.append(order)
                            
                except Exception as ex:
                    log_message(f"❌ [ORDER EXECUTION FAILED] Error: {ex}")
                    success = False
                    
                if len(order_results) > 0:
                    # Log trade
                    trade_record = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "direction": opportunity["direction"],
                        "trade_size_usd": trade_size,
                        "gross_return_pct": max(ret_A, ret_B) * 100.0,
                        "net_return_pct": opportunity["net_return"] * 100.0,
                        "profit_usd": trade_size * opportunity["net_return"],
                        "success": success,
                        "legs": [
                            {
                                "symbol": order.get("symbol", "N/A"),
                                "side": order.get("side", "N/A"),
                                "amount": order.get("amount", 0.0),
                                "price": order.get("average", order.get("price", 0.0)),
                                "status": order.get("status", "N/A")
                            } for order in order_results
                        ]
                    }
                    
                    state = load_state()
                    # Turn off force_execute in state to prevent endless spam
                    state["force_execute"] = False
                    state["trades"].append(trade_record)
                    if success:
                        state["accumulated_profit_usd"] += trade_record["profit_usd"]
                    save_state(state)
                    log_message(f"Arbitrage record added. Accumulated profit: ${state['accumulated_profit_usd']:.2f}")
                    
                # Pause to let markets settle
                log_message("Sleeping 30 seconds for settling...")
                if not sleep_checking_stop(30):
                    break
                
        except Exception as e:
            log_message(f"⚠️ Error in daemon loop cycle: {e}")
            traceback.print_exc()
            
        if not sleep_checking_stop(5):
            break

if __name__ == "__main__":
    # Handle start CLI flags
    if len(sys.argv) > 1 and sys.argv[1] in ["--start", "--daemon"]:
        state = load_state()
        state["is_running"] = True
        save_state(state)
        
    state = load_state()
    if state.get("is_running", False):
        try:
            run_arbitrage()
        except KeyboardInterrupt:
            log_message("Daemon stopped manually via console.")
        finally:
            state = load_state()
            state["is_running"] = False
            state["pid"] = None
            state["starting"] = False
            save_state(state)
            log_message("Daemon stopped.")
    else:
        log_message("is_running is False in state. Daemon will not run.")
