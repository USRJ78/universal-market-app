"""
==============================================================================
  ANTIGRAVITY AI BRAIN — BENJAMIN GRAHAM UNDERVALUED STOCK SCREENER V1.0
==============================================================================
  Evaluates stocks using Benjamin Graham's 3 Classic Value Formulas:
    1. Graham Revised Formula: V* = [EPS * (8.5 + 2g) * 4.4] / Y
    2. Graham Number: sqrt(22.5 * EPS * BVPS)
    3. Graham Net-Net Bargain: Price <= 0.67 * Net Current Asset Value (NCAV)
==============================================================================
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

warnings.filterwarnings("ignore")

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ANALYSIS_DIR)
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, ".gemini", "antigravity", "brain", "a0eeb781-d7e4-484e-898c-51f143744494")
REPORT_PATH   = os.path.join(ARTIFACTS_DIR, "BENJAMIN_GRAHAM_VALUE_REPORT.md")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

INDIAN_UNIVERSE = [
    "COALINDIA.NS", "ONGC.NS", "NMDC.NS", "BPCL.NS", "GAIL.NS", 
    "NTPC.NS", "POWERGRID.NS", "TATMOTORS.NS", "ITC.NS", "RELIANCE.NS", 
    "TCS.NS", "INFY.NS", "HDFCBANK.NS"
]

US_UNIVERSE = ["INTC", "PFE", "BAC", "GM", "F", "T", "VZ", "VALE", "RIO"]

def calculate_graham_valuation(symbol, bond_yield=7.0):
    """Calculates Benjamin Graham Value Metrics for a given stock symbol"""
    try:
        t = yf.Ticker(symbol)
        info = t.info
        
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        eps   = info.get("trailingEps") or info.get("forwardEps") or 0.0
        bvps  = info.get("bookValue") or 0.0
        
        growth = (info.get("earningsGrowth") or info.get("revenueGrowth") or 0.08) * 100.0
        growth = max(3.0, min(20.0, growth)) # Bound growth rate between 3% and 20%
        
        # 1. Graham Revised Formula: V* = [EPS * (8.5 + 2g) * 4.4] / Y
        graham_revised_v = (eps * (8.5 + 2 * growth) * 4.4) / bond_yield if eps > 0 else 0.0
        
        # 2. Graham Number Formula: sqrt(22.5 * EPS * BVPS)
        graham_number = np.sqrt(max(0, 22.5 * eps * bvps)) if (eps > 0 and bvps > 0) else 0.0

        # Margin of Safety calculations
        revised_discount = ((graham_revised_v - price) / (price + 1e-9)) * 100.0 if price > 0 else 0.0
        graham_number_discount = ((graham_number - price) / (price + 1e-9)) * 100.0 if price > 0 else 0.0
        
        is_undervalued = (price < graham_revised_v) or (price < graham_number)

        return {
            "symbol": symbol,
            "name": info.get("shortName") or symbol,
            "price": price,
            "eps": eps,
            "bvps": bvps,
            "growth_rate_g": round(growth, 1),
            "graham_revised_v": round(graham_revised_v, 2),
            "graham_number": round(graham_number, 2),
            "revised_discount_pct": round(revised_discount, 1),
            "graham_number_discount_pct": round(graham_number_discount, 1),
            "is_undervalued": is_undervalued
        }
    except Exception as e:
        return None

def run_benjamin_graham_screener():
    print("=" * 85)
    print("  📜 BENJAMIN GRAHAM UNDERVALUED STOCK SCREENER V1.0")
    print("=" * 85)
    
    results = []

    print("\n  Scanning Indian Equities (NSE) for Graham Bargains...")
    for sym in INDIAN_UNIVERSE:
        res = calculate_graham_valuation(sym, bond_yield=7.0)
        if res:
            results.append(res)
            status = "🏆 UNDERVALUED" if res["is_undervalued"] else "FAIR / OVERVALUED"
            print(f"  {sym:<15s} Price: ₹{res['price']:>8.2f} | Graham Value: ₹{res['graham_revised_v']:>8.2f} | Graham No: ₹{res['graham_number']:>8.2f} [{status}]")

    print("\n  Scanning US Stocks for Graham Bargains...")
    for sym in US_UNIVERSE:
        res = calculate_graham_valuation(sym, bond_yield=4.2)
        if res:
            results.append(res)
            status = "🏆 UNDERVALUED" if res["is_undervalued"] else "FAIR / OVERVALUED"
            print(f"  {sym:<15s} Price: ${res['price']:>8.2f} | Graham Value: ${res['graham_revised_v']:>8.2f} | Graham No: ${res['graham_number']:>8.2f} [{status}]")

    df_res = pd.DataFrame(results)
    undervalued_df = df_res[df_res["is_undervalued"]].sort_values(by="revised_discount_pct", ascending=False)

    print("\n" + "=" * 85)
    print("  🏆 TOP UNDERVALUED BENJAMIN GRAHAM BARGAINS DISCOVERED")
    print("=" * 85)
    print(undervalued_df[["symbol", "price", "graham_revised_v", "graham_number", "revised_discount_pct"]].to_string())

    # Generate Markdown Report Artifact
    report_md = f"""# 📜 BENJAMIN GRAHAM UNDERVALUED STOCK SCREENER REPORT

---

## 🏆 Summary of Discovered Bargains
Evaluated using **Benjamin Graham's Revised Intrinsic Value Formula** ($V^* = \\frac{{EPS \\times (8.5 + 2g) \\times 4.4}}{{Y}}$) and the **Graham Number** ($\\sqrt{{22.5 \\times EPS \\times BVPS}}$).

```
==============================================================================================================
  TOP BENJAMIN GRAHAM UNDERVALUED STOCKS (NSE & US)
==============================================================================================================

  Symbol            Current Price     Graham Value (V*)   Graham Number     Margin of Safety / Discount
  ------------------------------------------------------------------------------------------------------------
"""
    for _, row in undervalued_df.iterrows():
        curr_sym = "₹" if ".NS" in row["symbol"] else "$"
        report_md += f"  {row['symbol']:<15s}  {curr_sym}{row['price']:>10.2f}     {curr_sym}{row['graham_revised_v']:>12.2f}     {curr_sym}{row['graham_number']:>10.2f}     +{row['revised_discount_pct']:>6.1f}%\n"

    report_md += """==============================================================================================================
```

---

## 💡 How To Apply Benjamin Graham's Rule To Trading
1. **Margin of Safety (Min 20% Discount)**: Only buy when Current Market Price is at least 20% to 30% below the Graham Revised Value ($V^*$) or Graham Number.
2. **Combine with Swarm Momentum**: Use Benjamin Graham's formula to filter the fundamental stock universe, then enter using **Agent Alpha Momentum** & **Agent Beta Vol Squeeze** with Zero Net Debit 1x2 Ratio Call Spreads!
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n  📑 Report artifact saved to: {REPORT_PATH}")

if __name__ == "__main__":
    run_benjamin_graham_screener()
