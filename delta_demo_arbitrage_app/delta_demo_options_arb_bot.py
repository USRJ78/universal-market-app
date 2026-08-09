# delta_demo_options_arb_bot.py
import os
import sys
import time
import json
import ccxt
import traceback
from datetime import datetime

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# API Keys from API_KEYS.txt for Mainnet
DEMO_API = "qsNKMuPZyeubUK7rpqligKksNO0tey"
DEMO_SECRET = "jjMmELW0NEENLvkHqVTCx6iQNJNzFI8EFeLkY7V7lb3NVfmteX4iOUE5ClNH"
ENDPOINT = "https://cdn-ind.testnet.deltaex.org"

# Resolve paths relative to this script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "delta_demo_options_arb_state.json")
LOG_FILE = os.path.join(BASE_DIR, "delta_demo_options_arb.log")

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    # Strip non-ASCII/emojis for log file stability on Windows CMD
    safe_formatted = "".join(c for c in formatted if ord(c) < 128 or c in ['📐', '📈', '🟢', '🔴', '🔥', '⚡', '🤖', '❌', '⚠️', '📋', '📚', '🎉', '➕', '➖', '💸'])
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
                state = json.load(f)
                # Ensure new keys exist
                if "auto_unwind" not in state:
                    state["auto_unwind"] = True
                if "active_position" not in state:
                    state["active_position"] = None
                return state
        except Exception as e:
            log_message(f"Error loading state file: {e}")
    # Default State
    return {
        "is_running": False,
        "force_execute": False,
        "auto_unwind": True,
        "min_profit_pct": 0.01,
        "trade_size_usd": 100.0,
        "leverage": 20,
        "accumulated_profit_usd": 0.0,
        "active_position": None,
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

def calculate_post_tax_profit(loop, call_price, put_price, perp_price, strike, tax_rate=0.30):
    """
    Simulates the post-tax profit of an options parity loop at expiry over a price grid.
    Reflects the Indian tax rule where gains are taxed flat at 30% but losses cannot be offset.
    """
    import numpy as np
    # Grid of potential expiry prices from 80% to 120% of current perp price
    expiry_prices = np.linspace(perp_price * 0.8, perp_price * 1.2, 100)
    post_tax_profits = []
    
    for S in expiry_prices:
        if loop == 'A':  # Buy Call, Sell Put, Sell Perp (Short)
            call_pnl = max(0.0, S - strike) - call_price
            put_pnl = put_price - max(0.0, strike - S)
            perp_pnl = perp_price - S
        else:  # Sell Call, Buy Put, Buy Perp (Long)
            call_pnl = call_price - max(0.0, S - strike)
            put_pnl = max(0.0, strike - S) - put_price
            perp_pnl = S - perp_price
            
        # Tax paid on gains of individual legs with NO offsetting of losses
        tax_paid = tax_rate * (max(0.0, call_pnl) + max(0.0, put_pnl) + max(0.0, perp_pnl))
        net_pnl = (call_pnl + put_pnl + perp_pnl) - tax_paid
        post_tax_profits.append(net_pnl)
        
    return float(np.mean(post_tax_profits))

def run_arbitrage():
    state = load_state()
    state["pid"] = os.getpid()
    state["is_running"] = True
    state["starting"] = False
    save_state(state)

    log_message("==================================================")
    log_message(f"⚡ BOOTING DELTA EXCHANGE OPTIONS ARBITRAGE DAEMON (PID: {os.getpid()})")
    log_message("==================================================")
    
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
    
    try:
        log_message("Loading exchange markets...")
        markets = exchange.load_markets()
        log_message(f"Markets loaded successfully. Total symbols: {len(exchange.symbols)}")
        
        log_message("Verifying balance...")
        bal = exchange.fetch_balance()
        log_message(f"USDT/USD Balances fetched. Free USD Margin: {bal.get('USD', {}).get('free', 0.0)} USD")
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
                
            min_profit_pct = state.get("min_profit_pct", 0.01)
            trade_size_usd = state.get("trade_size_usd", 100.0)
            leverage = state.get("leverage", 20)
            force_execute = state.get("force_execute", False)
            auto_unwind = state.get("auto_unwind", True)
            active_position = state.get("active_position")
            
            loop_count += 1
            
            # CASE 1: Monitor and auto-unwind existing active position
            if active_position:
                if loop_count % 6 == 1:
                    log_message(f"Monitoring active options arbitrage position: {active_position['underlying']} Strike {active_position['strike']} (Loop {active_position['loop']})")
                
                # Fetch tickers
                tickers = exchange.fetch_tickers()
                
                # Extract leg symbols
                perp_symbol = active_position["legs"]["perp"]["symbol"]
                call_symbol = active_position["legs"]["call"]["symbol"]
                put_symbol = active_position["legs"]["put"]["symbol"]
                
                c_ticker = tickers.get(call_symbol)
                p_ticker = tickers.get(put_symbol)
                u_ticker = tickers.get(perp_symbol)
                
                if c_ticker and p_ticker and u_ticker:
                    c_bid = c_ticker.get('bid')
                    c_ask = c_ticker.get('ask')
                    p_bid = p_ticker.get('bid')
                    p_ask = p_ticker.get('ask')
                    u_bid = u_ticker.get('bid')
                    u_ask = u_ticker.get('ask')
                    
                    if all(x is not None for x in [c_bid, c_ask, p_bid, p_ask, u_bid, u_ask]):
                        qty = active_position["qty"]
                        
                        # Find contract size
                        market_perp = markets.get(perp_symbol)
                        contract_size = market_perp.get('contractSize') or 1.0
                        
                        total_units = qty * contract_size
                        
                        # Calculate exit value and entry cost
                        # Loop A entry was: buy Call, sell Put, short Perp.
                        # Unwind A is: sell Call, buy Put, buy Perp (Long).
                        # Unwind A cash flow = CallBid - PutAsk - PerpAsk
                        # Loop B entry was: sell Call, buy Put, buy Perp.
                        # Unwind B is: buy Call, sell Put, sell Perp (Short).
                        # Unwind B cash flow = - CallAsk + PutBid + PerpBid
                        
                        if active_position["loop"] == "A":
                            entry_cost_per_unit = active_position["legs"]["call"]["entry_price"] - active_position["legs"]["put"]["entry_price"] - active_position["legs"]["perp"]["entry_price"]
                            exit_value_per_unit = c_bid - p_ask - u_ask
                        else:
                            entry_cost_per_unit = active_position["legs"]["put"]["entry_price"] - active_position["legs"]["call"]["entry_price"] + active_position["legs"]["perp"]["entry_price"]
                            exit_value_per_unit = p_bid - c_ask + u_bid
                            
                        gross_pnl_usd = (exit_value_per_unit - entry_cost_per_unit) * total_units
                        
                        # Taker fees on unwind (approx 0.11% of perp price)
                        est_exit_fees = total_units * u_ask * 0.0011
                        net_pnl_usd = gross_pnl_usd - est_exit_fees
                        
                        if loop_count % 6 == 1:
                            log_message(f"Active Position PnL: Gross: ${gross_pnl_usd:+.4f} | Est Exit Fees: ${est_exit_fees:.4f} | Net: ${net_pnl_usd:+.4f} USD")
                            
                        # If net profit is positive and auto-unwind is active, trigger exit!
                        if auto_unwind and net_pnl_usd > 0.01:
                            log_message(f"🚀 AUTO-UNWIND TRIGGERED! Net Profit: ${net_pnl_usd:.4f} USD is positive. Placing exit orders...")
                            
                            unwind_results = []
                            unwind_success = True
                            
                            try:
                                try:
                                    fresh_tickers = exchange.fetch_tickers()
                                except Exception as t_err:
                                    log_message(f"Warning fetching fresh tickers: {t_err}")
                                    fresh_tickers = {}

                                if active_position["loop"] == "A":
                                    # Unwind Loop A: Sell Call, Buy Put, Buy Perp
                                    # Buy Perp: Buy limit at ask * 1.005
                                    perp_ticker = fresh_tickers.get(perp_symbol, {})
                                    perp_ask = perp_ticker.get('ask')
                                    if perp_ask:
                                        l_price = perp_ask * 1.005
                                        log_message(f"Unwinding Perp: Placing Buy limit order on {perp_symbol} for {qty} contracts @ limit price ${l_price:,.2f} (best ask ${perp_ask:,.2f})...")
                                        o_perp = exchange.create_limit_buy_order(perp_symbol, qty, l_price, params={'reduceOnly': True})
                                    else:
                                        log_message(f"Unwinding Perp: Placing Buy market order on {perp_symbol} for {qty} contracts...")
                                        o_perp = exchange.create_market_buy_order(perp_symbol, qty, params={'reduceOnly': True})
                                    unwind_results.append(o_perp)
                                    
                                    # Sell Call: Sell limit at bid * 0.995
                                    call_ticker = fresh_tickers.get(call_symbol, {})
                                    call_bid = call_ticker.get('bid')
                                    if call_bid:
                                        l_price = call_bid * 0.995
                                        log_message(f"Unwinding Call: Placing Sell limit order on {call_symbol} for {qty} contracts @ limit price ${l_price:,.2f} (best bid ${call_bid:,.2f})...")
                                        o_call = exchange.create_limit_sell_order(call_symbol, qty, l_price, params={'reduceOnly': True})
                                    else:
                                        log_message(f"Unwinding Call: Placing Sell market order on {call_symbol} for {qty} contracts...")
                                        o_call = exchange.create_market_sell_order(call_symbol, qty, params={'reduceOnly': True})
                                    unwind_results.append(o_call)
                                    
                                    # Buy Put: Buy limit at ask * 1.005
                                    put_ticker = fresh_tickers.get(put_symbol, {})
                                    put_ask = put_ticker.get('ask')
                                    if put_ask:
                                        l_price = put_ask * 1.005
                                        log_message(f"Unwinding Put: Placing Buy limit order on {put_symbol} for {qty} contracts @ limit price ${l_price:,.2f} (best ask ${put_ask:,.2f})...")
                                        o_put = exchange.create_limit_buy_order(put_symbol, qty, l_price, params={'reduceOnly': True})
                                    else:
                                        log_message(f"Unwinding Put: Placing Buy market order on {put_symbol} for {qty} contracts...")
                                        o_put = exchange.create_market_buy_order(put_symbol, qty, params={'reduceOnly': True})
                                    unwind_results.append(o_put)
                                else:
                                    # Unwind Loop B: Buy Call, Sell Put, Sell Perp
                                    # Sell Perp: Sell limit at bid * 0.995
                                    perp_ticker = fresh_tickers.get(perp_symbol, {})
                                    perp_bid = perp_ticker.get('bid')
                                    if perp_bid:
                                        l_price = perp_bid * 0.995
                                        log_message(f"Unwinding Perp: Placing Sell limit order on {perp_symbol} for {qty} contracts @ limit price ${l_price:,.2f} (best bid ${perp_bid:,.2f})...")
                                        o_perp = exchange.create_limit_sell_order(perp_symbol, qty, l_price, params={'reduceOnly': True})
                                    else:
                                        log_message(f"Unwinding Perp: Placing Sell market order on {perp_symbol} for {qty} contracts...")
                                        o_perp = exchange.create_market_sell_order(perp_symbol, qty, params={'reduceOnly': True})
                                    unwind_results.append(o_perp)
                                    
                                    # Buy Call: Buy limit at ask * 1.005
                                    call_ticker = fresh_tickers.get(call_symbol, {})
                                    call_ask = call_ticker.get('ask')
                                    if call_ask:
                                        l_price = call_ask * 1.005
                                        log_message(f"Unwinding Call: Placing Buy limit order on {call_symbol} for {qty} contracts @ limit price ${l_price:,.2f} (best ask ${call_ask:,.2f})...")
                                        o_call = exchange.create_limit_buy_order(call_symbol, qty, l_price, params={'reduceOnly': True})
                                    else:
                                        log_message(f"Unwinding Call: Placing Buy market order on {call_symbol} for {qty} contracts...")
                                        o_call = exchange.create_market_buy_order(call_symbol, qty, params={'reduceOnly': True})
                                    unwind_results.append(o_call)
                                    
                                    # Sell Put: Sell limit at bid * 0.995
                                    put_ticker = fresh_tickers.get(put_symbol, {})
                                    put_bid = put_ticker.get('bid')
                                    if put_bid:
                                        l_price = put_bid * 0.995
                                        log_message(f"Unwinding Put: Placing Sell limit order on {put_symbol} for {qty} contracts @ limit price ${l_price:,.2f} (best bid ${put_bid:,.2f})...")
                                        o_put = exchange.create_limit_sell_order(put_symbol, qty, l_price, params={'reduceOnly': True})
                                    else:
                                        log_message(f"Unwinding Put: Placing Sell market order on {put_symbol} for {qty} contracts...")
                                        o_put = exchange.create_market_sell_order(put_symbol, qty, params={'reduceOnly': True})
                                    unwind_results.append(o_put)
                                    
                                log_message("🎉 Auto-unwind orders executed successfully!")
                            except Exception as unwind_err:
                                log_message(f"❌ Auto-unwind order failed: {unwind_err}")
                                unwind_success = False
                                
                            if len(unwind_results) > 0:
                                # Save closed trade record
                                trade_record = {
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "loop": active_position["loop"],
                                    "underlying": active_position["underlying"],
                                    "expiry": active_position["expiry"],
                                    "strike": active_position["strike"],
                                    "qty": qty,
                                    "net_return_pct": (net_pnl_usd / (total_units * u_ask)) * 100,
                                    "profit_usd": net_pnl_usd if unwind_success else 0.0,
                                    "success": unwind_success,
                                    "type": "INTRA_DAY_CLOSE",
                                    "legs": [
                                        {
                                            "symbol": order.get("symbol", "N/A"),
                                            "side": order.get("side", "N/A"),
                                            "amount": order.get("amount", 0.0),
                                            "price": order.get("average", order.get("price", 0.0)),
                                            "id": order.get("id", "N/A")
                                        } for order in unwind_results
                                    ]
                                }
                                
                                state = load_state()
                                state["trades"].append(trade_record)
                                state["active_position"] = None
                                if unwind_success:
                                    state["accumulated_profit_usd"] += net_pnl_usd
                                save_state(state)
                                log_message(f"Active position closed. Realized PnL: ${net_pnl_usd:.4f} USD. Total profit: ${state['accumulated_profit_usd']:.4f} USD")
                                
                            # Cool down
                            if not sleep_checking_stop(30):
                                break
                            continue
                            
            # CASE 2: Scan and enter new positions
            else:
                if loop_count % 12 == 1:
                    log_message(f"Heartbeat: scanning options markets... Min Profit: {min_profit_pct}%, Size: ${trade_size_usd:.2f}")
                    
                tickers = exchange.fetch_tickers()
                
                # Map Call/Put pairs
                options_by_key = {}
                for symbol, m in markets.items():
                    if m.get('option'):
                        underlying = m.get('underlying') or m.get('base')
                        if underlying in ['BTC', 'ETH']:
                            expiry = m.get('expiryDatetime')
                            strike = m.get('strike')
                            opt_type = m.get('optionType')
                            if expiry and strike is not None and opt_type:
                                expiry_str = expiry.split('T')[0]
                                key = (underlying, expiry_str, strike)
                                if key not in options_by_key:
                                    options_by_key[key] = {}
                                options_by_key[key][opt_type] = symbol
                                
                opportunities = []
                for (underlying, expiry_str, strike), pair in options_by_key.items():
                    # Filter out short-term expiries (less than 3 days) to avoid post-only disruption
                    exp_dt = datetime.strptime(expiry_str, "%Y-%m-%d")
                    days_to_expiry = (exp_dt - datetime.today()).days
                    if days_to_expiry < 3:
                        continue
                        
                    call_symbol = pair.get('call')
                    put_symbol = pair.get('put')
                    
                    if not call_symbol or not put_symbol:
                        continue
                        
                    c_ticker = tickers.get(call_symbol)
                    p_ticker = tickers.get(put_symbol)
                    
                    if not c_ticker or not p_ticker:
                        continue
                        
                    c_bid = c_ticker.get('bid')
                    c_ask = c_ticker.get('ask')
                    p_bid = p_ticker.get('bid')
                    p_ask = p_ticker.get('ask')
                    
                    if c_bid is None or c_ask is None or p_bid is None or p_ask is None:
                        continue
                        
                    perp_symbol = 'BTC/USD:USD' if underlying == 'BTC' else 'ETH/USD:USD'
                    u_ticker = tickers.get(perp_symbol)
                    
                    if not u_ticker or u_ticker.get('bid') is None or u_ticker.get('ask') is None:
                        continue
                        
                    u_bid = u_ticker['bid']
                    u_ask = u_ticker['ask']
                    
                    # Loop A: Buy Call, Sell Put, Sell Perp (Short)
                    pre_tax_profit_A = p_bid - c_ask + u_bid - strike
                    pre_tax_pct_A = pre_tax_profit_A / u_bid * 100
                    profit_A = calculate_post_tax_profit('A', c_ask, p_bid, u_bid, strike)
                    pct_A = profit_A / u_bid * 100
                    
                    # Loop B: Sell Call, Buy Put, Buy Perp (Long)
                    pre_tax_profit_B = c_bid - p_ask - u_ask + strike
                    pre_tax_pct_B = pre_tax_profit_B / u_ask * 100
                    profit_B = calculate_post_tax_profit('B', c_bid, p_ask, u_ask, strike)
                    pct_B = profit_B / u_ask * 100
                    
                    est_fees_pct = 0.11
                    net_pct_A = pct_A - est_fees_pct
                    net_pct_B = pct_B - est_fees_pct
                    
                    if net_pct_A >= min_profit_pct:
                        opportunities.append({
                            'loop': 'A',
                            'underlying': underlying,
                            'perp_symbol': perp_symbol,
                            'call_symbol': call_symbol,
                            'put_symbol': put_symbol,
                            'strike': strike,
                            'expiry': expiry_str,
                            'profit_usd_per_unit': profit_A,
                            'pre_tax_profit_usd': pre_tax_profit_A,
                            'pre_tax_pct': pre_tax_pct_A,
                            'net_profit_pct': net_pct_A,
                            'call_price': c_ask,
                            'put_price': p_bid,
                            'perp_price': u_bid
                        })
                    elif net_pct_B >= min_profit_pct:
                        opportunities.append({
                            'loop': 'B',
                            'underlying': underlying,
                            'perp_symbol': perp_symbol,
                            'call_symbol': call_symbol,
                            'put_symbol': put_symbol,
                            'strike': strike,
                            'expiry': expiry_str,
                            'profit_usd_per_unit': profit_B,
                            'pre_tax_profit_usd': pre_tax_profit_B,
                            'pre_tax_pct': pre_tax_pct_B,
                            'net_profit_pct': net_pct_B,
                            'call_price': c_bid,
                            'put_price': p_ask,
                            'perp_price': u_ask
                        })
                        
                if force_execute and not opportunities:
                    best_force = None
                    best_force_val = -999999
                    for (underlying, expiry_str, strike), pair in options_by_key.items():
                        # Expiry days filter
                        exp_dt = datetime.strptime(expiry_str, "%Y-%m-%d")
                        days_to_expiry = (exp_dt - datetime.today()).days
                        if days_to_expiry < 3: continue
                        
                        call_symbol = pair.get('call')
                        put_symbol = pair.get('put')
                        if not call_symbol or not put_symbol: continue
                        c_ticker, p_ticker = tickers.get(call_symbol), tickers.get(put_symbol)
                        if not c_ticker or not p_ticker: continue
                        c_bid, c_ask = c_ticker.get('bid'), c_ticker.get('ask')
                        p_bid, p_ask = p_ticker.get('bid'), p_ticker.get('ask')
                        if c_bid is None or c_ask is None or p_bid is None or p_ask is None: continue
                        perp_symbol = 'BTC/USD:USD' if underlying == 'BTC' else 'ETH/USD:USD'
                        u_ticker = tickers.get(perp_symbol)
                        if not u_ticker or u_ticker.get('bid') is None or u_ticker.get('ask') is None: continue
                        u_bid, u_ask = u_ticker['bid'], u_ticker['ask']
                        
                        pre_tax_profit_A = p_bid - c_ask + u_bid - strike
                        pre_tax_pct_A = pre_tax_profit_A / u_bid * 100
                        profit_A = calculate_post_tax_profit('A', c_ask, p_bid, u_bid, strike)
                        pct_A = profit_A / u_bid * 100
                        
                        pre_tax_profit_B = c_bid - p_ask - u_ask + strike
                        pre_tax_pct_B = pre_tax_profit_B / u_ask * 100
                        profit_B = calculate_post_tax_profit('B', c_bid, p_ask, u_ask, strike)
                        pct_B = profit_B / u_ask * 100
                        
                        if pct_A > best_force_val:
                            best_force_val = pct_A
                            best_force = {
                                'loop': 'A', 'underlying': underlying, 'perp_symbol': perp_symbol,
                                'call_symbol': call_symbol, 'put_symbol': put_symbol, 'strike': strike,
                                'expiry': expiry_str, 'profit_usd_per_unit': profit_A,
                                'pre_tax_profit_usd': pre_tax_profit_A, 'pre_tax_pct': pre_tax_pct_A,
                                'net_profit_pct': pct_A - 0.11,
                                'call_price': c_ask, 'put_price': p_bid, 'perp_price': u_bid
                            }
                        if pct_B > best_force_val:
                            best_force_val = pct_B
                            best_force = {
                                'loop': 'B', 'underlying': underlying, 'perp_symbol': perp_symbol,
                                'call_symbol': call_symbol, 'put_symbol': put_symbol, 'strike': strike,
                                'expiry': expiry_str, 'profit_usd_per_unit': profit_B,
                                'pre_tax_profit_usd': pre_tax_profit_B, 'pre_tax_pct': pre_tax_pct_B,
                                'net_profit_pct': pct_B - 0.11,
                                'call_price': c_bid, 'put_price': p_ask, 'perp_price': u_ask
                            }
                    if best_force:
                        opportunities.append(best_force)
                        log_message("Force execution triggered: Selecting best available parity loop.")
                        
                if opportunities:
                    opportunities = sorted(opportunities, key=lambda x: x['net_profit_pct'], reverse=True)
                    opt = opportunities[0]
                    
                    log_message(f"🔥 OPPORTUNITY DETECTED! Net Spread: {opt['net_profit_pct']:.3f}% | Loop: {opt['loop']} | {opt['underlying']} Expiry {opt['expiry']} Strike {opt['strike']}")
                    
                    market_perp = markets.get(opt['perp_symbol'])
                    contract_size = market_perp.get('contractSize') or 1.0
                    
                    qty_contracts = round(trade_size_usd / (contract_size * opt['perp_price']))
                    if qty_contracts < 1:
                        qty_contracts = 1
                        
                    log_message(f"Calculated trade size: {qty_contracts} contracts (approx ${qty_contracts * contract_size * opt['perp_price']:.2f} USD exposure)")
                    
                    # Check free margin
                    bal = exchange.fetch_balance()
                    free_usd = bal.get('USD', {}).get('free', 0.0)
                    est_margin = (qty_contracts * contract_size * opt['perp_price']) / leverage
                    if est_margin > free_usd:
                        log_message(f"❌ Insufficient USD margin. Required: ${est_margin:.2f}, Free: ${free_usd:.2f}")
                        state = load_state()
                        state["force_execute"] = False
                        save_state(state)
                        if not sleep_checking_stop(30):
                            break
                        continue
                        
                    try:
                        log_message(f"Setting leverage to {leverage}x on {opt['perp_symbol']}...")
                        exchange.set_leverage(leverage, opt['perp_symbol'])
                    except Exception as ex:
                        log_message(f"Warning setting leverage: {ex}")
                        
                    try:
                        fresh_tickers = exchange.fetch_tickers()
                    except Exception as t_err:
                        log_message(f"Warning fetching fresh tickers: {t_err}")
                        fresh_tickers = {}

                    success = True
                    order_results = []
                    
                    try:
                        if opt['loop'] == 'A':
                            # Short Perp: Sell limit at bid * 0.995
                            perp_ticker = fresh_tickers.get(opt['perp_symbol'], {})
                            perp_bid = perp_ticker.get('bid')
                            if perp_bid:
                                l_price = perp_bid * 0.995
                                log_message(f"Placing Short Perp limit order on {opt['perp_symbol']} for {qty_contracts} contracts @ limit price ${l_price:,.2f} (best bid ${perp_bid:,.2f})...")
                                o_perp = exchange.create_limit_sell_order(opt['perp_symbol'], qty_contracts, l_price)
                            else:
                                log_message(f"Placing Short Perp market order on {opt['perp_symbol']} for {qty_contracts} contracts...")
                                o_perp = exchange.create_market_sell_order(opt['perp_symbol'], qty_contracts)
                            order_results.append(o_perp)
                            
                            # Buy Call: Buy limit at ask * 1.005
                            call_ticker = fresh_tickers.get(opt['call_symbol'], {})
                            call_ask = call_ticker.get('ask')
                            if call_ask:
                                l_price = call_ask * 1.005
                                log_message(f"Placing Buy Call limit order on {opt['call_symbol']} for {qty_contracts} contracts @ limit price ${l_price:,.2f} (best ask ${call_ask:,.2f})...")
                                o_call = exchange.create_limit_buy_order(opt['call_symbol'], qty_contracts, l_price)
                            else:
                                log_message(f"Placing Buy Call market order on {opt['call_symbol']} for {qty_contracts} contracts...")
                                o_call = exchange.create_market_buy_order(opt['call_symbol'], qty_contracts)
                            order_results.append(o_call)
                            
                            # Sell Put: Sell limit at bid * 0.995
                            put_ticker = fresh_tickers.get(opt['put_symbol'], {})
                            put_bid = put_ticker.get('bid')
                            if put_bid:
                                l_price = put_bid * 0.995
                                log_message(f"Placing Sell Put limit order on {opt['put_symbol']} for {qty_contracts} contracts @ limit price ${l_price:,.2f} (best bid ${put_bid:,.2f})...")
                                o_put = exchange.create_limit_sell_order(opt['put_symbol'], qty_contracts, l_price)
                            else:
                                log_message(f"Placing Sell Put market order on {opt['put_symbol']} for {qty_contracts} contracts...")
                                o_put = exchange.create_market_sell_order(opt['put_symbol'], qty_contracts)
                            order_results.append(o_put)
                        else:
                            # Long Perp: Buy limit at ask * 1.005
                            perp_ticker = fresh_tickers.get(opt['perp_symbol'], {})
                            perp_ask = perp_ticker.get('ask')
                            if perp_ask:
                                l_price = perp_ask * 1.005
                                log_message(f"Placing Long Perp limit order on {opt['perp_symbol']} for {qty_contracts} contracts @ limit price ${l_price:,.2f} (best ask ${perp_ask:,.2f})...")
                                o_perp = exchange.create_limit_buy_order(opt['perp_symbol'], qty_contracts, l_price)
                            else:
                                log_message(f"Placing Long Perp market order on {opt['perp_symbol']} for {qty_contracts} contracts...")
                                o_perp = exchange.create_market_buy_order(opt['perp_symbol'], qty_contracts)
                            order_results.append(o_perp)
                            
                            # Sell Call: Sell limit at bid * 0.995
                            call_ticker = fresh_tickers.get(opt['call_symbol'], {})
                            call_bid = call_ticker.get('bid')
                            if call_bid:
                                l_price = call_bid * 0.995
                                log_message(f"Placing Sell Call limit order on {opt['call_symbol']} for {qty_contracts} contracts @ limit price ${l_price:,.2f} (best bid ${call_bid:,.2f})...")
                                o_call = exchange.create_limit_sell_order(opt['call_symbol'], qty_contracts, l_price)
                            else:
                                log_message(f"Placing Sell Call market order on {opt['call_symbol']} for {qty_contracts} contracts...")
                                o_call = exchange.create_market_sell_order(opt['call_symbol'], qty_contracts)
                            order_results.append(o_call)
                            
                            # Buy Put: Buy limit at ask * 1.005
                            put_ticker = fresh_tickers.get(opt['put_symbol'], {})
                            put_ask = put_ticker.get('ask')
                            if put_ask:
                                l_price = put_ask * 1.005
                                log_message(f"Placing Buy Put limit order on {opt['put_symbol']} for {qty_contracts} contracts @ limit price ${l_price:,.2f} (best ask ${put_ask:,.2f})...")
                                o_put = exchange.create_limit_buy_order(opt['put_symbol'], qty_contracts, l_price)
                            else:
                                log_message(f"Placing Buy Put market order on {opt['put_symbol']} for {qty_contracts} contracts...")
                                o_put = exchange.create_market_buy_order(opt['put_symbol'], qty_contracts)
                            order_results.append(o_put)
                            
                        log_message("🎉 Arbitrage execution completed successfully!")
                    except Exception as ord_err:
                        log_message(f"❌ Order placement failed: {ord_err}")
                        success = False
                        
                    if len(order_results) > 0:
                        # Write active position details to track unwinding PnL
                        act_pos_record = {
                            "loop": opt['loop'],
                            "underlying": opt['underlying'],
                            "expiry": opt['expiry'],
                            "strike": opt['strike'],
                            "qty": qty_contracts,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "legs": {
                                "perp": {
                                    "symbol": opt['perp_symbol'],
                                    "entry_price": opt['perp_price']
                                },
                                "call": {
                                    "symbol": opt['call_symbol'],
                                    "entry_price": opt['call_price']
                                },
                                "put": {
                                    "symbol": opt['put_symbol'],
                                    "entry_price": opt['put_price']
                                }
                            }
                        }
                        
                        state = load_state()
                        state["force_execute"] = False
                        if success:
                            state["active_position"] = act_pos_record
                        save_state(state)
                        log_message("Active position recorded in state for auto-unwind tracking.")
                        
                    # Cool down
                    log_message("Sleeping 30 seconds to let markets settle...")
                    if not sleep_checking_stop(30):
                        break
                        
            if not sleep_checking_stop(10):
                break
                
        except Exception as loop_ex:
            log_message(f"⚠️ Error in daemon cycle: {loop_ex}")
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
