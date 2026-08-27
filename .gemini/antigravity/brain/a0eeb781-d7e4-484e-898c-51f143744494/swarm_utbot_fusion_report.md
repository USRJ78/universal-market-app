# SWARM CALL SPREAD × UTBOT FUSION ENGINE — 10-YEAR REPORT

## Strategy Architecture

```
ENTRY — 5-Layer Conviction Gate:

  Layer 1  [Swarm Alpha]    Price >= 98% of 52-week High + EMA20 > EMA50
  Layer 2  [Swarm Beta]     ATR10 / ATR50 < 0.92  (volatility squeeze)
  Layer 3  [Swarm Gamma]    S&D Position 10%-85%  (not in supply zone)
  Layer 4  [UTBot]          Trailing ATR crossover fires BUY (Key=2.4, ATR=9)
  Layer 5  [Supertrend]     Close > Supertrend(10,3) line  (macro trend)

  Conviction Score = 20% per layer
  FUSION 70%  threshold: >= 3 layers agree simultaneously
  FUSION 100% threshold: ALL 5 layers agree simultaneously

EXECUTION — Zero Net Debit 1x2 Ratio Call Spread:
  Buy  1x ATM Call  @ K1 = entry price
  Sell 2x OTM Call  @ K2 = K1 x 1.045 (+4.5% above)
  Net debit  ≈ zero
  Max profit:  at K2 = +4.5% x 6x options leverage = +27% on allocated margin
  Stop loss:   -3% of allocated margin (net debit trigger)
  Catastrophic exit: if price > 10% above entry (buyback short calls)
```

## Top 15 Results

| Asset | Strategy | Final ($1k) | CAGR | Win Rate | Trades | MDD |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Bitcoin** | UTBot Only | **$12,089.61** | +26.8% | **47.8%** | 136 | -6.05% |
| **Infosys** | UTBot Only | **$8,370.71** | +22.7% | **51.0%** | 98 | -4.36% |
| **Reliance** | UTBot Only | **$6,339.80** | +19.4% | **47.0%** | 100 | -2.89% |
| **Bitcoin** | Fusion 70% | **$4,721.57** | +16.0% | **51.4%** | 74 | -2.77% |
| **NIFTY 50** | UTBot Only | **$4,251.41** | +14.9% | **55.7%** | 88 | -3.50% |
| **Bank NIFTY** | UTBot Only | **$4,138.17** | +14.6% | **55.7%** | 79 | -4.36% |
| **Infosys** | Fusion 70% | **$3,731.67** | +13.5% | **58.3%** | 48 | -3.50% |
| **Bank NIFTY** | Fusion 70% | **$2,358.11** | +8.6% | **63.0%** | 46 | -2.64% |
| **NIFTY 50** | Fusion 70% | **$2,242.20** | +8.1% | **67.3%** | 49 | -3.15% |
| **Reliance** | Fusion 70% | **$2,066.75** | +7.2% | **44.4%** | 45 | -3.50% |
| **Bitcoin** | Swarm Only | **$2,035.43** | +7.0% | **71.4%** | 21 | -2.64% |
| **Infosys** | Swarm Only | **$1,610.82** | +4.7% | **57.9%** | 19 | -2.64% |
| **NIFTY 50** | Swarm Only | **$1,500.11** | +4.0% | **51.4%** | 37 | -2.07% |
| **Bank NIFTY** | Swarm Only | **$1,295.63** | +2.5% | **44.0%** | 25 | -2.93% |
| **Reliance** | Swarm Only | **$1,277.69** | +2.4% | **37.5%** | 16 | -3.50% |


## How To Use This On TradingView

```
CHECKLIST (scan daily or 4H charts):
  [ ] Price within 2% of 52-week high         (Swarm Alpha)
  [ ] EMA20 line above EMA50 line             (Swarm Alpha)
  [ ] ATR10 noticeably tighter than ATR50     (Swarm Beta — vol squeeze)
  [ ] UTBot fires BUY arrow on your chart     (UTBot layer)
  [ ] Supertrend background is GREEN          (Supertrend layer)
  [ ] S&D position not near top of range      (S&D layer)

IF 4-5 of these checkboxes are ticked → EXECUTE the 1x2 Call Spread
IF all 5 are ticked → MAXIMUM CONVICTION — larger position size
```

---

![Fusion Chart](file:///C:\Users\USER\OneDrive\Documents\universal-market-app\.gemini\antigravity\brain\a0eeb781-d7e4-484e-898c-51f143744494\swarm_utbot_fusion_chart.png)
