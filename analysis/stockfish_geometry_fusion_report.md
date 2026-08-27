# ♟️ STOCKFISH x MARKET GEOMETRY HYBRID FUSION ENGINE — 10-YEAR REPORT (2016–2026)

## Strategy Architecture
- **Market Universe**: ALL 1,916 NSE Equities (`EQUITY_L.csv`)
- **Hybrid Conviction Score**:
  $$\text{FusionScore} = 0.50 \times \text{Stockfish FEN Score} + 0.50 \times \text{3D Geometry Score}$$
- **Rules**:
  - `FusionScore >= 0.60` $\rightarrow$ **Buy Stock Position**
  - `FusionScore < 0.30` or `VolComp > 0.80` $\rightarrow$ **Exit Position**
  - **Take Profit**: +15.0%
  - **Stop Loss**: -4.0%

## Performance Metrics

| Metric | Result |
|:---|:---:|
| **Starting Capital** | **₹1,00,000.00** (INR 1 Lakh) |
| **Final Capital** | 🏆 **₹85,895,874.76** |
| **Total Net Return** | **+85,795.87%** (859.0x Growth) |
| **Annualized CAGR** | **+96.52% / Year** |
| **Win Rate** | **45.0%** (3682 Wins / 8180 Trades) |
| **Max Drawdown (MDD)** | 🛡️ **-67.24%** |
| **Total Trades Executed** | 8180 |

---

![Stockfish Fusion Chart](file:///C:/Users/USER/OneDrive/Documents/universal-market-app/analysis/stockfish_geometry_fusion_chart.png)
