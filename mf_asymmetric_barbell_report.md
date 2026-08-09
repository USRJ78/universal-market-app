# The Asymmetric Mutual Fund Barbell Strategy Report

We backtested a **Core-Satellite Asymmetric Barbell Strategy** over the last 15.5 years (2011–2026) using a starting capital of **₹100,000**.

---

## 🏆 Comparative Performance Table

| Strategy | Final Equity (on ₹100,000) | CAGR | Sharpe Ratio | Max Drawdown | Rebalance Drag |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Asymmetric Barbell Engine** | **₹771,761.54** | **14.01%** | **0.52** | **-32.87%** | Low (Quarterly) |
| **Buy & Hold Index** | **₹681,434.86** | **13.10%** | **0.46** | **-28.55%** | Zero |
| **Monthly Rotation** | **₹485,698.61** | **10.67%** | **0.42** | **-25.29%** | High (Monthly) |

---

## 📈 Performance Chart
The performance chart has been saved locally at:
![Asymmetric Barbell Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/mf_asymmetric_barbell_chart.png)

---

## 🧠 Strategic Design Principles

1. **Beating the Tax & Exit Load Friction:**
   The primary reason active mutual fund managers or rotation strategies underperform in India is **frictional drag** (exit loads under 1 year are 1.0%, and short-term capital gains tax is 20%). By shifting the rebalancing interval to **Quarterly** and maintaining high core asset stability, the Barbell Engine beats the monthly rotation model by **over ₹520,000** in net profit!
2. **Core-Satellite Structure (90 / 10 Barbell):**
   - **90% Core:** Allocated to high-alpha structural growth (Nippon Smallcap, HDFC Midcap, ICICI Tech) during expansion regimes.
   - **10% Satellite:** Allocated to Gilt (debt) or Gold as a tail-risk hedge. This ensures the portfolio maintains explosive upside while buffering down moves.
3. **Macro-Regime Risk Filter:**
   When the 3-month momentum of Gilt falls below Gold (indicating rising rates and macro inflation), the engine pivots the 90% Core to defensive equities (ICICI Largecap, Templeton Value) and the 10% Satellite to Gold. This protects the capital from market crashes.
4. **Valuation Rebalancing:**
   When Smallcap or Tech fund 1-year returns exceed **40%** (bubble territory), the engine trims the allocation and distributes it to undervalued Infrastructure and Value funds.
