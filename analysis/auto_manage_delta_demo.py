"""
==============================================================================
  DELTA DEMO OPTIONS POSITION MONITOR & ENGINE
==============================================================================

PURPOSE:
  Tracks live 1x2 Ratio Call Spread options positions on Delta Demo Testnet.

USAGE:
  python analysis/auto_manage_delta_demo.py --status
  python analysis/auto_manage_delta_demo.py --close
==============================================================================
"""

import sys, ccxt

API_KEY = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
SECRET  = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"

def init_delta():
    exchange = ccxt.delta({
        'apiKey': API_KEY,
        'secret': SECRET,
        'enableRateLimit': True,
    })
    exchange.urls['api']['public']  = 'https://cdn-ind.testnet.deltaex.org'
    exchange.urls['api']['private'] = 'https://cdn-ind.testnet.deltaex.org'
    return exchange


def check_or_close():
    exchange = init_delta()
    print("=" * 65)
    print("  DELTA DEMO 1x2 RATIO OPTION SPREAD MONITOR")
    print("=" * 65)

    try:
        positions = exchange.fetch_positions()
        active = [p for p in positions if float(p['info'].get('size', 0)) != 0]

        if not active:
            print("  No active options positions found on Delta Demo Testnet.")
            return

        total_pnl = 0.0
        for p in active:
            info = p['info']
            symbol = info.get('product_symbol')
            size   = float(info.get('size', 0))
            entry  = float(info.get('entry_price', 0))
            mark   = float(info.get('mark_price', 0))
            pnl    = float(info.get('unrealized_pnl', 0))
            total_pnl += pnl

            leg_type = "LONG 1x ATM CALL" if size > 0 else "SHORT 2x OTM CALL"
            print(f"  Leg        : {leg_type} ({symbol})")
            print(f"  Size       : {size} contract(s)")
            print(f"  Entry Price: ${entry:,.2f}")
            print(f"  Mark Price : ${mark:,.2f}")
            print(f"  Unrealized : ${pnl:,.6f} USD")
            print("-" * 65)

        print(f"  COMBINED RATIO SPREAD PnL: ${total_pnl:,.6f} USD")
        print("=" * 65)

        if "--close" in sys.argv:
            print("\n  Closing all active option legs ...")
            for p in active:
                info = p['info']
                prod = info.get('product_symbol')
                size = float(info.get('size', 0))
                side = "sell" if size > 0 else "buy"
                amt  = abs(int(size))
                order = exchange.create_order(symbol=prod, type="market", side=side, amount=amt)
                print(f"  [CLOSED] {prod} ({side.upper()} {amt}) | Order ID: {order.get('id')}")

    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    check_or_close()
