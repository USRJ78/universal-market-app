import ccxt
import json
import sys
import os

# Import credentials from the bot
try:
    from delta_demo_geometry_bot import DEMO_API, DEMO_SECRET
except ImportError:
    print("Could not import credentials from delta_demo_geometry_bot.py")
    sys.exit(1)

def check_positions():
    print("Authenticating with Delta Testnet...")
    exchange = ccxt.delta({
        'apiKey': DEMO_API,
        'secret': DEMO_SECRET,
        'enableRateLimit': True
    })
    
    # Switch to testnet
    exchange.set_sandbox_mode(True)

    try:
        positions = exchange.fetch_positions()
        active_positions = [p for p in positions if float(p['info'].get('size', 0)) != 0]
        
        print(f"Total Active Positions: {len(active_positions)}")
        print("-" * 50)
        
        for pos in active_positions:
            symbol = pos['symbol']
            side = pos['side']
            size = pos['info'].get('size')
            entry_price = pos['entryPrice']
            mark_price = pos['markPrice']
            unrealized_pnl = pos['unrealizedPnl']
            
            print(f"Symbol: {symbol}")
            print(f"  Side: {side}")
            print(f"  Size: {size}")
            print(f"  Entry Price: {entry_price}")
            print(f"  Mark Price:  {mark_price}")
            print(f"  Unrealized PnL: {unrealized_pnl}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error fetching positions: {e}")

if __name__ == "__main__":
    check_positions()
