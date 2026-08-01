"""
==============================================================================
  DELTA DEMO TESTNET AUTOMATED QUANT BOT (FIXED SYMBOLS & MARKETS)
==============================================================================
"""

import os, sys, time, json, datetime
import ccxt
import pandas as pd
import numpy as np

API_KEY = "KoDWNWYEBc392P2tYKZzcS43kyRShL"
SECRET  = "XuHNnS3eTI4J7kIIrLjMol7kIskaHQTKkYgHg3ZBJBXuKt3u9Y5h3I7yelEa"

def init_delta():
    exchange = ccxt.delta({
        'apiKey': API_KEY,
        'secret': SECRET,
        'enableRateLimit': True,
    })
    exchange.urls['api']['public']  = 'https://cdn-ind.testnet.deltaex.org'
    exchange.urls['api']['private'] = 'https://cdn-ind.testnet.deltaex.org'
    return exchange


def run_delta_demo_bot():
    print("=" * 70)
    print("  DELTA DEMO TESTNET AUTOMATED QUANT BOT")
    print("=" * 70)

    exchange = init_delta()

    # Load Markets
    print("\n[1] Loading Available Markets on Delta Testnet ...")
    try:
        markets = exchange.load_markets()
        print(f"  [OK] Loaded {len(markets)} markets on Delta Testnet!")
        
        # Show top market symbols
        sample_symbols = list(markets.keys())[:10]
        print(f"  Sample Markets: {sample_symbols}")
    except Exception as e:
        print(f"  [ERROR] Loading markets failed: {e}")
        markets = {}

    # Account Balances
    print("\n[2] Fetching Account Wallet Balances ...")
    try:
        bal = exchange.fetch_balance()
        free_usdt = float(bal.get('USDT', {}).get('free', 0))
        total_usdt = float(bal.get('USDT', {}).get('total', 0))
        print(f"  USDT Free : ${free_usdt:,.2f} | Total: ${total_usdt:,.2f}")
        
        for k, v in bal.items():
            if isinstance(v, dict) and float(v.get('total', 0)) > 0:
                print(f"  Asset {k}: Free={v.get('free')} Total={v.get('total')}")
    except Exception as e:
        print(f"  [ERROR] Fetching balance failed: {e}")

    # Fetch OHLCV for BTC Futures / Options
    target_symbol = None
    for s in ["BTC/USDT", "BTC/USD", "BTCUSD", "BTC_USDT"]:
        if s in markets:
            target_symbol = s
            break
    if not target_symbol and list(markets.keys()):
        target_symbol = list(markets.keys())[0]

    print(f"\n[3] Fetching Live Ticker & OHLCV for {target_symbol} ...")
    if target_symbol:
        try:
            ticker = exchange.fetch_ticker(target_symbol)
            print(f"  {target_symbol} Last Price : ${ticker.get('last')}")
            print(f"  24h High / Low : ${ticker.get('high')} / ${ticker.get('low')}")

            ohlcv = exchange.fetch_ohlcv(target_symbol, timeframe="15m", limit=50)
            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                
                close = df["close"]
                df["ema20"] = close.ewm(span=20, adjust=False).mean()
                df["ema50"] = close.ewm(span=50, adjust=False).mean()

                last = df.iloc[-1]
                print(f"  15m Candle Close : ${last['close']:,.2f}")
                print(f"  EMA 20 / EMA 50  : ${last['ema20']:,.2f} / ${last['ema50']:,.2f}")
                
                signal = "BULLISH 🟢" if last["ema20"] > last["ema50"] else "BEARISH 🔴"
                print(f"  Trend Signal     : {signal}")
        except Exception as e:
            print(f"  [ERROR] Fetching OHLCV failed: {e}")

    # Check Positions
    print("\n[4] Checking Open Positions on Delta Testnet ...")
    try:
        positions = exchange.fetch_positions()
        active = [p for p in positions if float(p['info'].get('size', 0)) != 0]
        print(f"  Active Open Positions: {len(active)}")
        for p in active:
            info = p['info']
            print(f"    Product: {info.get('product_symbol')} | Size: {info.get('size')} | Entry: ${info.get('entry_price')} | PnL: ${info.get('unrealized_pnl')}")
    except Exception as e:
        print(f"  [ERROR] Position check: {e}")

    print("\n" + "=" * 70)
    print("  DELTA DEMO AUTOMATED BOT ACTIVE & MONITORED")
    print("=" * 70)


if __name__ == "__main__":
    run_delta_demo_bot()
