import ccxt
import pprint
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
        
        test_symbol = 'BTC/USD:USD'
        if test_symbol in markets:
            print(f"\nFetching ticker for {test_symbol}...")
            ticker = exchange.fetch_ticker(test_symbol)
            print("Ticker successfully fetched:")
            # Use pprint to safe string format it, or print directly
            pprint.pprint(ticker)
            
            print("\nMarket details:")
            pprint.pprint(markets[test_symbol])
            
            # Let's inspect the keys inside the 'info' dict of the ticker to locate the funding rate!
            print("\nInfo keys in ticker:")
            info = ticker.get('info', {})
            pprint.pprint(info)
            
            # Print specifically funding rate or interest rate fields if present
            print("\nFunding Rate related fields:")
            for k, v in info.items():
                if 'funding' in k or 'rate' in k or 'interest' in k:
                    print(f" - {k}: {v}")
                    
    except Exception as e:
        print(f"Error inspecting data: {e}")

if __name__ == "__main__":
    inspect_data()
