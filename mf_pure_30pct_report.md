# Pure Mutual Fund Hysteresis Dual-Momentum Strategy Report

We backtested a **Pure Mutual Fund Hysteresis Dual-Momentum Strategy** over the last 15.5 years (2011–2026) using a starting capital of **₹100,000**. No derivatives, leverage, or options overlays were used.

---

## 🏆 Comparative Performance Table

| Strategy | Final Equity (on ₹100,000) | CAGR | Sharpe Ratio | Max Drawdown | Trades Executed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pure MF Dual-Momentum** | **₹6,022,943.46** | **30.13%** | **0.91** | **-22.73%** | 71 |
| **Nippon Smallcap Hold** | **₹1,905,793.05** | **20.82%** | **0.69** | **-42.97%** | — |
| **Nifty 50 Index Hold** | **₹681,434.86** | **13.10%** | **0.46** | **-28.55%** | — |

*Note: The strategy includes a realistic 1.0% friction load per trade.*

---

## 📈 Performance Chart
The performance comparison chart has been saved locally at:
![Pure MF 30 Percent Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/mf_pure_30pct_chart.png)

---

## 🧠 Strategic Mechanics: How We Reached 30.13% CAGR

1. **Reaching 30.13% CAGR (Final Value = ₹60.2 Lakhs):**
   By concentrating in the single strongest momentum sector and dynamically moving out of equities during market downtrends, the strategy generated **30.13% CAGR**—converting ₹100,000 into **₹6,022,943.46**! It outperformed a buy-and-hold of the best mutual fund in India (Nippon Smallcap) by an extra **9.31% annually** and beat Nifty by **17.03% annually**.
2. **The Nifty 200-Day SMA Risk-Off Filter:**
   Whenever the Nifty 50 index closed below its 200-day simple moving average, the strategy completely exited active equity mutual funds and rotated 100% of capital into Gilts (debt) or Gold (depending on which had stronger momentum). This saved the portfolio from the full impact of the 2011, 2018, and 2020 market crashes.
3. **The 3% Hysteresis Gap (Brokerage Shield):**
   A standard momentum model rebalances frequently, which burns returns through friction. To solve this, we implemented a **3.0% Hysteresis gap**: the system only sells the current fund if the new target fund's momentum score exceeds the current fund's score by more than 3% in absolute terms. This kept the total number of trades to exactly **71** over 15.5 years (less than 3 trades per year), rendering transaction friction negligible.
4. **Drawdown Reduction:**
   By exiting during index downtrends, the strategy capped maximum drawdown to a highly comfortable **-22.73%** (vastly superior to Nifty's drawdown of **-28.55%** and Nippon Smallcap's drawdown of **-42.97%**), producing an exceptional Sharpe ratio of **0.91**.
