"""
==============================================================================
  ANTIGRAVITY AI BRAIN — BROAD BENJAMIN GRAHAM MARKET SCREENER V2.0
==============================================================================
  Scans broad universe across Large, Mid, Small, and Micro-Cap Equities
  to count TOTAL number of companies undervalued under Graham's Formula:
    V* = [EPS * (8.5 + 2g) * 4.4] / Y
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
REPORT_PATH   = os.path.join(ARTIFACTS_DIR, "BROAD_GRAHAM_MARKET_COUNT_REPORT.md")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# Broad Multi-Cap Universe (Large, Mid, Small, Micro Cap)
BROAD_UNIVERSE = [
    # Large Cap (NSE)
    "COALINDIA.NS", "ONGC.NS", "BPCL.NS", "GAIL.NS", "NTPC.NS", "POWERGRID.NS", 
    "HDFCBANK.NS", "SBIN.NS", "ICICIBANK.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS",
    "ITC.NS", "IOC.NS", "HINDALCO.NS", "VEDL.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    
    # Mid Cap & Public Sector Undertakings (NSE)
    "NMDC.NS", "OIL.NS", "REC.NS", "PFC.NS", "NHPC.NS", "SJVN.NS", "IRFC.NS", 
    "HUDCO.NS", "BEL.NS", "HAL.NS", "NATIONALUM.NS", "MOIL.NS", "GUJGASLTD.NS",
    "PETRONET.NS", "HPCL.NS", "MRPL.NS", "GSFC.NS", "GNFC.NS", "FACT.NS",
    
    # Small & Micro Cap Value Stocks (NSE)
    "GMDC.NS", "RAILTEL.NS", "RCF.NS", "NFL.NS", "CHENNPETRO.NS", "HINDPETRO.NS",
    "KIOCL.NS", "COCHINSHIP.NS", "GRSE.NS", "MAZDOCK.NS", "BHEL.NS", "ENGINERSIN.NS",
    
    # US Multi-Cap Stocks
    "INTC", "PFE", "BAC", "GM", "F", "T", "VZ", "VALE", "RIO", "BTI", "MO", "XOM", "CVX", "WFC", "C"
]

def scan_broad_graham_universe():
    print("=" * 85)
    print("  📜 BROAD BENJAMIN GRAHAM MARKET COUNT SCREENER INITIALIZED")
    print("=" * 85)
    print(f"  Scanning broad universe of {len(BROAD_UNIVERSE)} companies across all market caps...")

    results = []
    
    for sym in BROAD_UNIVERSE:
        try:
            t = yf.Ticker(sym)
            info = t.info
            
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
            eps   = info.get("trailingEps") or info.get("forwardEps") or 0.0
            bvps  = info.get("bookValue") or 0.0
            mcap  = info.get("marketCap") or 0.0
            
            if price <= 0 or eps <= 0:
                continue

            growth = (info.get("earningsGrowth") or info.get("revenueGrowth") or 0.08) * 100.0
            growth = max(3.0, min(20.0, growth))

            bond_yield = 7.0 if ".NS" in sym else 4.2
            
            # Graham Revised Formula
            graham_v = (eps * (8.5 + 2 * growth) * 4.4) / bond_yield
            graham_no = np.sqrt(max(0, 22.5 * eps * bvps)) if bvps > 0 else 0.0

            discount_v  = ((graham_v - price) / price) * 100.0
            discount_no = ((graham_no - price) / price) * 100.0 if graham_no > 0 else 0.0

            is_undervalued = (price < graham_v) or (price < graham_no)

            cap_category = "Large Cap" if mcap > 200000000000 else ("Mid Cap" if mcap > 50000000000 else ("Small Cap" if mcap > 10000000000 else "Micro Cap"))

            results.append({
                "symbol": sym,
                "name": info.get("shortName") or sym,
                "category": cap_category,
                "price": price,
                "eps": eps,
                "graham_value": round(graham_v, 2),
                "graham_number": round(graham_no, 2),
                "discount_pct": round(discount_v, 1),
                "is_undervalued": is_undervalued
            })
        except Exception:
            continue

    df = pd.DataFrame(results)
    undervalued_df = df[df["is_undervalued"]].sort_values(by="discount_pct", ascending=False)

    total_scanned = len(df)
    total_undervalued = len(undervalued_df)
    undervalued_pct = (total_undervalued / max(1, total_scanned)) * 100.0

    print("\n" + "=" * 85)
    print("  🏆 BENJAMIN GRAHAM MARKET COUNT RESULTS")
    print("=" * 85)
    print(f"  Total Companies Scanned:        {total_scanned}")
    print(f"  TOTAL UNDERVALUED COMPANIES:    {total_undervalued} ({undervalued_pct:.1f}% of market universe)")
    print(f"  Total Overvalued / Fair:        {total_scanned - total_undervalued}")
    print("=" * 85)

    # Market Cap Breakdown
    print("\n  📊 UNDERVALUED BREAKDOWN BY MARKET CAP CATEGORY:")
    cap_summary = undervalued_df["category"].value_counts()
    for cat, count in cap_summary.items():
        print(f"  - {cat:<12s}: {count} Companies Undervalued")

    print("\n  📋 TOP UNDERVALUED BARGAINS (BY MARGIN OF SAFETY):")
    print(undervalued_df[["symbol", "category", "price", "graham_value", "discount_pct"]].head(15).to_string())

    # Write Markdown Report Artifact
    report_md = f"""# 📜 BROAD BENJAMIN GRAHAM MARKET COUNT REPORT

---

## 🏆 Market-Wide Undervalued Count Summary
Out of **{total_scanned} companies scanned** across Large, Mid, Small, and Micro-Cap Equities:

- **TOTAL UNDERVALUED COMPANIES**: **`{total_undervalued}`** (**`{undervalued_pct:.1f}%`** of total market universe)
- **Total Fair / Overvalued**: `{total_scanned - total_undervalued}`

---

## 📊 Undervalued Breakdown By Market Cap

```
==============================================================================================================
  MARKET CAP BREAKDOWN OF BENJAMIN GRAHAM BARGAINS
==============================================================================================================

  Market Cap Category        Undervalued Company Count    Percentage Share
  ------------------------------------------------------------------------------------------------------------
"""
    for cat, count in cap_summary.items():
        pct_share = (count / total_undervalued) * 100.0
        report_md += f"  {cat:<25s}  {count:>5d} Companies           {pct_share:>6.1f}%\n"

    report_md += """==============================================================================================================
```

---

## 📋 Complete List of Undervalued Companies

```
==============================================================================================================
  COMPLETE LIST OF BENJAMIN GRAHAM UNDERVALUED STOCKS
==============================================================================================================

  Symbol           Category       Current Price    Graham Value (V*)   Discount (%)
  ------------------------------------------------------------------------------------------------------------
"""
    for _, row in undervalued_df.iterrows():
        curr_sym = "₹" if ".NS" in row["symbol"] else "$"
        report_md += f"  {row['symbol']:<15s}  {row['category']:<12s}   {curr_sym}{row['price']:>10.2f}       {curr_sym}{row['graham_value']:>12.2f}       +{row['discount_pct']:>6.1f}%\n"

    report_md += """==============================================================================================================
```
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n  📑 Report artifact saved to: {REPORT_PATH}")

if __name__ == "__main__":
    scan_broad_graham_universe()
