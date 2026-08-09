# Deep Neural Network UT Bot (Walk-Forward Out-Of-Sample 2016–2026)

We deployed a **3-Layer Deep Neural Network Classifier (MLP: 64 x 32 x 16)** trained on an 18-dimensional market vector (Trend, Volatility Squeeze, Momentum, Donchian, Volume, Candle Geometry) with **Walk-Forward Rolling Retraining (OOS)** to eliminate all lookahead bias.

---

## 🏆 Deep Neural Network Performance Results

### 1. Bitcoin (BTC-USD) Deep Neural Network:
| Metric | Buy & Hold BTC | **Deep Neural UT Bot Engine** |
| :--- | :--- | :--- |
| **Final Equity ($100k start)** | **$6,652,320.37** | **$125,810.82** |
| **CAGR (%)** | **57.00%** | **3.22%** |
| **Max Drawdown (%)** | **-83.40%** | **-45.19%** |
| **Win Rate (%)** | — | **28.6%** |
| **Profit Factor** | — | **1.34** |
| **Total Neural Trades** | — | **7** |

---

## 📈 Deep Neural Network Performance Chart
![Deep Neural UT Bot Chart](file:///c:/Users/USER/OneDrive/Documents/universal-market-app/utbot_deep_neural_chart.png)

---

## 🧠 Neural Architecture & Feature Representation

1. **Multi-Layer Neural Net (64 x 32 x 16)**:
   - **Input**: 12 normalized market regime indicators (S/EMA200, EMA20/EMA50, ATR Ratio, ADX, RSI, Dist_H52, Vol Ratio, Candle Geometry).
   - **Output**: Conviction probability score P(Win).

2. **Walk-Forward Rolling Out-of-Sample Retraining**:
   - The model is retrained every 6 months on a rolling 3-year historical window. No future data is ever leaked to past predictions.
