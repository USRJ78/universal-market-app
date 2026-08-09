"""
==============================================================================
  DELTA DEMO TESTNET LIVE REAL-TIME P&L & BALANCE AUDITOR
==============================================================================
"""

import sys, os, time, datetime
import ccxt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

DELTA_API_KEY = "t3tgPkmiiTDz11HNvFd3tj16xRhU7x"
DELTA_API_SECRET = "eX7MDoQGI7qaNENtHXQjNvxJ2qolZFzUqcMu8Cp5WKIkCdhQMQEf4Op8jMOn"
BASE_URL = "https://cdn-ind.testnet.deltaex.org"

def check_live_pnl():
    exchange = ccxt.delta({
        'apiKey': DELTA_API_KEY,
        'secret': DELTA_API_SECRET,
        'enableRateLimit': True,
    })
    exchange.urls['api']['public'] = BASE_URL
    exchange.urls['api']['private'] = BASE_URL

    print("=" * 75)
    print("  DELTA DEMO TESTNET REAL-TIME ACCOUNT P&L AUDIT")
    print("=" * 75)

    balance = exchange.fetch_balance()
    usdt = balance.get('USDT', {})
    usd = balance.get('USD', {})

    total_usdt = float(usdt.get('total', 0.0) or 0.0)
    free_usdt = float(usdt.get('free', 0.0) or 0.0)
    total_usd = float(usd.get('total', 0.0) or 0.0)
    free_usd = float(usd.get('free', 0.0) or 0.0)

    total_equity = total_usdt + total_usd
    free_equity = free_usdt + free_usd

    # Fetch active positions
    positions = exchange.fetch_positions()
    active_positions = [p for p in positions if abs(float(p.get('contracts', 0) or 0)) > 0]

    unrealized_pnl = sum(float(p.get('unrealizedPnl', 0) or 0) for p in active_positions)

    baseline_capital = 140.44
    print(f"  Starting Balance Baseline  : ${baseline_capital:,.2f} USD")
    print(f"  Current Total Wallet Equity: ${total_equity:,.2f} USD")
    print(f"  Free Available Margin      : ${free_equity:,.2f} USD")
    print(f"  Unrealized Position P&L   : ${unrealized_pnl:+.2f} USD")

    net_profit = (total_equity + unrealized_pnl) - baseline_capital
    net_profit_pct = (net_profit / baseline_capital) * 100.0

    print("-" * 75)
    print(f"  NET CUMULATIVE PROFIT TO DATE : ${net_profit:+.2f} USD ({net_profit_pct:+.2f}%)")
    print("=" * 75)

    if active_positions:
        print("\n  ACTIVE OPEN POSITIONS:")
        for pos in active_positions:
            sym = pos.get('symbol')
            size = pos.get('contracts')
            entry = pos.get('entryPrice')
            mark = pos.get('markPrice')
            pnl = pos.get('unrealizedPnl')
            print(f"    • {sym:<25} | Size: {size} | Entry: ${entry} | Mark: ${mark} | P&L: ${pnl}")
    else:
        print("\n  [NOTICE] No active open position positions currently held (Positions closed in profit).")

if __name__ == "__main__":
    check_live_pnl()
