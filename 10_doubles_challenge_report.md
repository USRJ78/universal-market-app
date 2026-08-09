# The 10 Doubles Challenge Report
## Goal: ₹1 Lakh → ₹10 Crore in 10 Years

### Strategy Layers
1. **Stockfish FEN Bot** — Weekly BTC price action mapped to chess board positions, evaluated by Stockfish engine (depth 10)
2. **UT Bot Trailing Stop** — ATR-based trailing stop (Key=2, Period=10) for dynamic exits
3. **2x Leverage** — Applied ONLY during confirmed triple-confluence Mega-Bull phases: Price > 200-SMA AND RSI between 50-70 AND Stockfish score >= 1.0
4. **INR denomination** — All returns computed in INR (BTC-USD × USDINR), capturing additional rupee depreciation alpha

### Results

| Metric | 10-Doubles Bot | BTC Buy & Hold |
|:---|:---|:---|
| Final Value | ₹2,962,380 | ₹936,657 |
| CAGR | 72.3% | 43.2% |
| Sharpe Ratio | 1.37 | 0.67 |
| Max Drawdown | -34.5% | -72.9% |
| Total Return | 30x | 9x |
| Doublings Hit | 5/10 | — |

### Doubling Timeline
- **Double #1** hit on **December 2020** → ₹216,206
- **Double #2** hit on **January 2021** → ₹491,046
- **Double #3** hit on **February 2021** → ₹847,649
- **Double #4** hit on **March 2024** → ₹1,914,957
- **Double #5** hit on **December 2024** → ₹3,290,265

### Key Mechanics
- **Stockfish exit signal** prevented holding through the 2018 crypto winter (-84%) and 2022 crash (-75%)
- **2x leverage** was activated only during confirmed bull phases, accelerating compounding during the 2020-2021 bull run
- **INR denomination** added ~3-4% extra annual alpha from USD/INR currency drift
- Total trades executed: **38** (averaging 4/year — very low friction)
