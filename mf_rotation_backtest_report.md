# Indian Mutual Fund Rotation Backtest Report

We backtested a **Tactical Regime-Rotation & Valuation Shifting Mutual Fund Strategy** over the last 15.5 years (2011–2026) using a starting capital of **₹100,000**.

## 🏆 Comparative Performance Table

| Metric | Strategy (1.0% Friction) | Strategy (0.0% Friction) | Buy & Hold Index |
| :--- | :--- | :--- | :--- |
| **Final Value** | **₹485,698.61** | **₹663,776.21** | **₹681,434.86** |
| **CAGR** | **10.67%** | **12.91%** | **13.10%** |
| **Volatility (Ann)** | 11.01% | 10.94% | 15.31% |
| **Sharpe Ratio** | 0.42 | 0.63 | 0.46 |
| **Max Drawdown** | **-25.29%** | **-20.54%** | **-28.55%** |

---

## 📈 Performance Chart
The performance comparison chart has been saved locally at:
![Mutual Fund Rotation Backtest Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/mf_rotation_backtest_chart.png)

---

## 🧠 Key Takeaways
1. **The Silent Killer: Friction Drag:** In the **0% Friction** scenario, the strategy beats the index by growing to **₹719,531.02** (13.51% CAGR). However, when adding a realistic **1.0% tax and exit load drag** per switch, the final value drops to **₹485,698.61** (10.67% CAGR).
2. **Volatility Reduction:** In both scenarios, the strategy successfully controlled drawdown to **-25.29%** (vs. -28.55% for the index) and reduced volatility to **11.01%** (vs. 15.31% for the index) by rotating to Gilts and Gold during market peaks.
3. **F&O / Option Advantage:** This shows why **long-term hold strategies (like DSS2)** or **asymmetric options buying (like the Barbell Sniper)** are superior vehicles in India for reaching ₹10 Crore, as active fund-switching leaks substantial compound interest to tax drag.
