# Nifty 50 10-Year UT Bot Alerts & Stop Loss Backtest Report (2016–2026)

We backtested the **UT Bot Alerts Strategy** with a **10% Stop Loss** on daily **Nifty 50 (^NSEI)** data over the last 10 years (July 2016 to July 2026) with a starting capital of **₹100,000**.

---

## 🏆 Comparative Performance Table

| Strategy | Final Equity (on ₹100,000) | CAGR | Sharpe Ratio | Max Drawdown | Total Trades |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Buy & Hold Nifty 50** | **₹292,866.50** | **11.35%** | **0.42** | **-38.44%** | — |
| **UT Bot (No Stop Loss)** | **₹264,593.74** | **10.22%** | **0.39** | **-26.06%** | 150 |
| **UT Bot + 10% Stop Loss** | **₹187,412.56** | **6.48%** | **0.15** | **-26.06%** | 150 |

*Note: All simulations include a realistic 0.1% transaction friction fee per trade.*

---

## 📈 Performance Chart
The performance comparison chart has been saved locally at:
![Nifty UT Bot 10 Year Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/nifty_utbot_10yr_chart.png)

---

## 🧠 Strategic Analysis: UT Bot Behavior on Nifty 50

1. **Underperforming Buy & Hold (Friction Leakage):**
   Unlike Bitcoin (which is a high-momentum asset with explosive multi-thousand-percent runs), Nifty 50 is a mean-reverting equity index. Applying a daily UT Bot strategy to Nifty leads to **whipsaws during sideways consolidations**, executing **150 trades** over 10 years. This high trading volume bleeds performance via transaction friction, dragging the CAGR to **10.22%** (underperforming Nifty's buy-and-hold at **11.35%**).
2. **Stop Loss Performance:**
   Similar to the BTC backtest, adding the **10% Stop Loss further degrades the performance to 6.48% CAGR** (Final Value = **₹187,412.56** vs. ₹264,593.74 for no stop loss). Because Nifty occasionally undergoes 10% pullbacks during standard market adjustments, the static stop loss repeatedly forces trades to exit at the local bottom.
3. **Drawdown Protection:**
   The primary benefit of the UT Bot on Nifty was **drawdown reduction**. The strategy reduced Nifty's maximum drawdown from **-38.44%** (during the 2020 COVID crash) to **-26.06%**. However, the cost in returns is significant.
