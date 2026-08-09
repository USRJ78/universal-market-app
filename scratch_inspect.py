import ccxt
import pprint

def inspect_data():
    print("Connecting to Delta Exchange public API...")
    exchange = ccxt.delta({'enableRateLimit': True})
    
    exchange.urls['api'] = {
        'public': 'https://api.india.delta.exchange',
        'private': 'https://api.india.delta.exchange'
    }
    
    try:
        markets = exchange.load_markets()
        print(f"Total active markets: {len(markets)}")
        
        # Look for BTC and ETH futures/swaps symbols
        btc_futures = []
        eth_futures = []
        for sym, m in markets.items():
            if not m.get('option'):
                if 'BTC' in sym:
                    btc_futures.append(sym)
                elif 'ETH' in sym:
                    eth_futures.append(sym)
                    
        print(f"\nFound {len(btc_futures)} BTC futures/swaps:")
        pprint.pprint(btc_futures[:10])
        
        print(f"\nFound {len(eth_futures)} ETH futures/swaps:")
        pprint.pprint(eth_futures[:10])
        
        # Test fetch_tickers with the actual found symbol
        if btc_futures:
            test_symbol = btc_futures[0]
            print(f"\nFetching ticker for {test_symbol}...")
            ticker = exchange.fetch_ticker(test_symbol)
            print("Ticker successfully fetched:")
            pprint.pprint(ticker)
            
            # Check if funding rate info is present in the ticker or market info
            print("\nMarket details:")
            pprint.pprint(markets[test_symbol])
            
    except Exception as e:
        print(f"Error inspecting data: {e}")

if __name__ == "__main__":
    inspect_data()
