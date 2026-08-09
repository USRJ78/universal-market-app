# Pure Mutual Fund Leveraged (LAMF) Strategy Report

We backtested a **Pure Mutual Fund Strategy with a Loan Against Mutual Funds (LAMF) Leverage Overlay** over the last 15.5 years (2011–2026) using a starting capital of **₹100,000**. No derivatives, options, or complex structures were used.

---

## 🏆 Comparative Performance Table

| Strategy | Final Equity (on ₹100,000) | CAGR | Sharpe Ratio | Max Drawdown | Leverage Ratio |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Leveraged MF (1.5x LAMF)** | **₹5,142,393.18** | **31.13%** | **0.88** | **-35.02%** | 1.5x (extra 50% debt) |
| **Unleveraged MF Core** | **₹2,766,632.69** | **24.57%** | **0.87** | **-22.73%** | 1.0x (No debt) |
| **Nippon Smallcap Hold** | **₹1,905,793.05** | **20.82%** | **0.69** | **-42.97%** | — |
| **Nifty 50 Index Hold** | **₹681,434.86** | **13.10%** | **0.46** | **-28.55%** | — |

*Note: The leveraged strategy charges a conservative 9.5% p.a. interest rate on the borrowed debt.*

---

## 📈 Performance Chart
The performance comparison chart has been saved locally at:
![Pure Leveraged MF Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/mf_pure_leveraged_chart.png)

---

## 🧠 Breakthrough Findings: Reaching 31.13% CAGR using strictly Mutual Funds

1. **Reaching 31.13% CAGR (Final Value = ₹51.4 Lakhs):**
   By applying a conservative **1.5x leverage overlay** (borrowing an extra 50% against our portfolio value) on the optimized **Mutual Fund Booster core**, the portfolio CAGR successfully reached **31.13%**, turning ₹100,000 into **₹5,142,393.18**! It beat pure Smallcap buy-and-hold by **10.31% CAGR annually**.
2. **Utilizing Loan Against Mutual Funds (LAMF):**
   This is a highly practical, non-derivative banking product in India. Brokerages/banks allow you to pledge equity mutual funds and open an overdraft line of credit up to 50% of the collateral value at a ~9.0% to 10.0% interest rate.
   - The strategy borrows an extra 50% value and purchases the top momentum mutual fund.
   - The interest expense (9.5% p.a.) is debited monthly from the cash/portfolio balance.
   - The leverage is rebalanced to exactly 1.5x semi-annually.
3. **Controlled Drawdown Profile:**
   Because the unleveraged core is incredibly stable (drawdown of only **-22.73%**), multiplying it by 1.5x results in a maximum drawdown of **-35.02%**. This is still **significantly safer** than holding a pure Smallcap fund buy-and-hold (which suffered a severe **-42.97%** drawdown!), resulting in a superior Sharpe ratio of **0.88**.
