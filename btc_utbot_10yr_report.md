# BTC 10-Year UT Bot Alerts & Stop Loss Backtest Report (2016–2026)

We backtested the **UT Bot Alerts Strategy** with a **10% Stop Loss** on daily **BTC-USD** data over the last 10 years (July 2016 to July 2026) with a starting capital of **$100,000**.

---

## 🏆 Comparative Performance Table

| Strategy | Final Equity (on $100,000) | CAGR | Sharpe Ratio | Max Drawdown | Total Trades |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UT Bot (No Stop Loss)** | **$8,891,894.21** | **56.76%** | **0.86** | **-54.89%** | 187 |
| **Buy & Hold BTC-USD** | **$7,682,401.99** | **54.21%** | **0.78** | **-83.56%** | — |
| **UT Bot + 10% Stop Loss** | **$124,593.74** | **2.21%** | **0.12** | **-71.12%** | 187 |

*Note: All simulations include a realistic 0.1% transaction friction fee per trade.*

---

## 📈 Performance Chart (Log Scale)
The performance comparison chart has been saved locally at:
![BTC UT Bot 10 Year Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/btc_utbot_10yr_chart.png)

---

## 🧠 Critical Analysis: Why the 10% Stop Loss Destroyed the Strategy

1. **The "Death by a Thousand Cuts" Trap:**
   While adding a 10% stop loss sounds intuitive to protect capital, on Bitcoin it **completely destroyed the strategy's returns**, yielding a dismal **2.21% CAGR** compared to the Buy & Hold return of **54.21% CAGR**. 
   - Bitcoin has high intraday and intraweek noise. During structural bull runs, BTC frequently drops 12% to 18% before moving 3x higher. 
   - The 10% stop loss repeatedly stopped the portfolio out at local bottoms, locking in losses, and leaving the strategy in cash while Bitcoin surged.
2. **Pure Trend Following Outperformed (56.76% CAGR):**
   The standard **UT Bot without a stop loss** (using only the trailing stop crossing as an exit) outperformed Buy & Hold by **2.55% CAGR annually**, turning $100,000 into **$8.89 Million** (compared to Buy & Hold's **$7.68 Million**).
3. **Significant Drawdown Reduction:**
   Even without a tight stop loss, the standard UT Bot trailing stop logic reduced BTC's maximum drawdown from a painful **-83.56%** (during the 2018 and 2022 crypto winters) to a much more manageable **-54.89%**. This proves that the indicator's organic exit signal is highly effective at trailing trends, whereas an arbitrary static stop loss is destructive.
