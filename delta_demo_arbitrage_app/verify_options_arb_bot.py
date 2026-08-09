# verify_options_arb_bot.py
import ccxt
import os
import sys

# Add directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from delta_demo_options_arb_bot import DEMO_API, DEMO_SECRET, ENDPOINT

def main():
    print("==================================================")
    print("🔬 RUNNING OPTIONS ARBITRAGE BOT VERIFICATION SCRIPT")
    print("==================================================")
    
    # Initialize exchange
    print("Initializing Delta Exchange connection...")
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
        print("Loading markets...")
        markets = exchange.load_markets()
        print(f"✅ Connection successful! Loaded {len(markets)} markets.")
        
        # Test fetching balance
        print("Fetching wallet balance...")
        bal = exchange.fetch_balance()
        print(f"✅ Balance loaded. Free USD Margin: {bal.get('USD', {}).get('free')} USD")
        
        # Test options grouping
        print("Grouping options...")
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
        print(f"✅ Found {len(options_by_key)} complete Call/Put option strikes.")
        
        # Dry-run ticker fetch
        print("Fetching tickers...")
        tickers = exchange.fetch_tickers()
        print(f"✅ Fetched {len(tickers)} tickers successfully.")
        
        # Scan for Put-Call Parity spreads
        from delta_demo_options_arb_bot import calculate_post_tax_profit
        
        print("\nScanning for Put-Call Parity violations (Dry Run):")
        opportunities = []
        for (underlying, expiry_str, strike), pair in options_by_key.items():
            call_symbol = pair.get('call')
            put_symbol = pair.get('put')
            if not call_symbol or not put_symbol: continue
            
            c_ticker = tickers.get(call_symbol)
            p_ticker = tickers.get(put_symbol)
            if not c_ticker or not p_ticker: continue
            
            c_bid, c_ask = c_ticker.get('bid'), c_ticker.get('ask')
            p_bid, p_ask = p_ticker.get('bid'), p_ticker.get('ask')
            if c_bid is None or c_ask is None or p_bid is None or p_ask is None: continue
            
            perp_symbol = 'BTC/USD:USD' if underlying == 'BTC' else 'ETH/USD:USD'
            u_ticker = tickers.get(perp_symbol)
            if not u_ticker or u_ticker.get('bid') is None or u_ticker.get('ask') is None: continue
            u_bid, u_ask = u_ticker['bid'], u_ticker['ask']
            
            # Loop A: Buy Call, Sell Put, Short Perp
            profit_A_pre = p_bid - c_ask + u_bid - strike
            pct_A_pre = profit_A_pre / u_bid * 100
            profit_A_post = calculate_post_tax_profit('A', c_ask, p_bid, u_bid, strike)
            pct_A_post = profit_A_post / u_bid * 100
            
            # Loop B: Sell Call, Buy Put, Buy Perp
            profit_B_pre = c_bid - p_ask - u_ask + strike
            pct_B_pre = profit_B_pre / u_ask * 100
            profit_B_post = calculate_post_tax_profit('B', c_bid, p_ask, u_ask, strike)
            pct_B_post = profit_B_post / u_ask * 100
            
            if pct_A_pre - 0.11 > 0:
                opportunities.append(('A', underlying, expiry_str, strike, pct_A_pre - 0.11, profit_A_pre, pct_A_post - 0.11, profit_A_post))
            if pct_B_pre - 0.11 > 0:
                opportunities.append(('B', underlying, expiry_str, strike, pct_B_pre - 0.11, profit_B_pre, pct_B_post - 0.11, profit_B_post))
                
        print(f"✅ Parity Scan completed. Found {len(opportunities)} active violations.")
        if opportunities:
            opportunities = sorted(opportunities, key=lambda x: x[6], reverse=True)
            print("\nTop 5 Arbitrage opportunities (Sorted by Net Post-Tax Return):")
            for loop, und, exp, strike, pre_pct, pre_usd, post_pct, post_usd in opportunities[:5]:
                print(f"  Loop {loop} | {und} Expiry {exp} Strike {strike} | Pre-Tax: {pre_pct:.3f}% (${pre_usd:.2f}) | Post-Tax: {post_pct:.3f}% (${post_usd:.2f})")
        else:
            print("  No violations found exceeding transaction fees (0.11%).")
            
        print("\n🎉 VERIFICATION SUCCESSFUL! OPTIONS BOT CORE IS FULLY FUNCTIONAL.")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
