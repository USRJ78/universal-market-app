# UTBOT + SUPERTREND ALIGNMENT — EXACT TRADINGVIEW PARAMETERS

## Setup (Matches Your TradingView Chart)

```
Indicator:    UT Bot Alerts
  Key Value:  5
  ATR Period: 1

Indicator:    Supertrend
  Period:     10
  Multiplier: 3.0

RULE:
  ✅ BUY  signal → ONLY valid when Supertrend is GREEN (bullish)
  ✅ SELL signal → ONLY valid when Supertrend is RED   (bearish)
  ❌ Counter-trend UTBot signals → IGNORED completely
```

## Results

| Asset | Strategy | Final ($1k) | CAGR | Win Rate | Trades | MDD |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| Bitcoin | No Filter | $2,980.91 | +10.9% | 43.8% | 233 | -17.53% |
| Bitcoin | ✅ **ST Aligned** | $2,164.82 | +7.6% | 52.9% | 121 | -22.41% |
| NIFTY 50 | No Filter | $1,007.08 | +0.1% | 46.8% | 154 | -4.73% |
| NIFTY 50 | ✅ **ST Aligned** | $1,104.30 | +0.9% | 65.5% | 87 | -7.05% |


## How Supertrend Alignment Blocks False Breakouts

When UTBot fires a BUY during a **RED Supertrend zone** (downtrend), it's a counter-trend signal —
price is likely to continue falling despite the momentary crossover. The Supertrend background
colour tells you the macro direction instantly. Only take UTBot signals that agree with that direction.

---

![Chart](file:///C:\Users\USER\OneDrive\Documents\universal-market-app\.gemini\antigravity\brain\a0eeb781-d7e4-484e-898c-51f143744494\utbot_tv_exact_params_chart.png)
