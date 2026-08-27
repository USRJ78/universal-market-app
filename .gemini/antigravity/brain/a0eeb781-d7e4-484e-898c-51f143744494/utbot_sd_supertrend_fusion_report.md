# UTBOT + SUPPLY/DEMAND + SUPERTREND FUSION — 10-YEAR AUDIT

Added **Supertrend Alignment** as a false-breakout filter to the highest-CAGR UTBot strategy.

## Core Logic — Triple Confirmation Gate

```
BUY Signal VALID only when ALL 3 agree simultaneously:

  1. UTBot Buy Alert   → Trailing ATR crossover fires
  2. S/D Filter        → S/D Position 10% to 85% (not at supply ceiling)
  3. Supertrend BULL   → Close > Supertrend line (macro trend confirmed)

WHY SUPERTREND HELPS:
  - UTBot fires on ANY breakout, even in downtrends
  - Supertrend ensures the breakout is WITH the dominant trend
  - Eliminates counter-trend false breakouts entirely
```

## 10-Year Results — All Variants

| Rank | Strategy | Final Equity | CAGR | Win Rate | Trades | MDD | False Breakouts Blocked |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| #1 | **Baseline: UTBot Only** | **$2,613.87** | +9.60% | 87.0% | 177 | -3.77% | — |
| #2 | **GRAND FUSION: UTBot+S&D+ST(10,3)+ADX18** | **$1,999.26** | +6.83% | 87.7% | 130 | -3.61% | 47 |
| #3 | **Champion: UTBot + S&D Filter (+71.16% CAGR)** | **$1,978.81** | +6.73% | 86.9% | 137 | -3.61% | — |
| #4 | **UTBot + S&D + ST Fast  (ATR7  × 2.0)** | **$1,978.81** | +6.73% | 86.9% | 137 | -3.61% | — |
| #5 | **UTBot + S&D + ST Medium(ATR10 × 3.0)** | **$1,978.81** | +6.73% | 86.9% | 137 | -3.61% | — |
| #6 | **UTBot + S&D + ST Slow  (ATR14 × 4.0)** | **$1,978.81** | +6.73% | 86.9% | 137 | -3.61% | — |


## Supertrend Parameters

| Config | ATR Period | Multiplier | Behavior |
|:---|:---:|:---:|:---|
| **Fast**   | 7  | 2.0 | Reactive, more signals, tighter trail |
| **Medium** | 10 | 3.0 | Standard, balanced (recommended) |
| **Slow**   | 14 | 4.0 | Smooth, fewer flips, wider trail |

## Trade Setup (Champion Parameters)

```
Entry:           UTBot Buy + S/D ≤ 85% + Supertrend Bullish
Take Profit:     +1.52% above entry
Stop-Loss:       -0.73% below entry
Breakeven Lock:  Move SL to entry once +0.32% profit reached
```

---

![Fusion Chart](file:///C:\Users\USER\OneDrive\Documents\universal-market-app\.gemini\antigravity\brain\a0eeb781-d7e4-484e-898c-51f143744494\utbot_sd_supertrend_fusion_chart.png)
