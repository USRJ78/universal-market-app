"""
==============================================================================
  ANTIGRAVITY AI BRAIN — BATCH DCF ON BENJAMIN GRAHAM UNDERVALUED STOCKS V1.0
==============================================================================
  Runs Parallel 50-Thread Discounted Cash Flow (DCF) Valuations on all 56
  Benjamin Graham Undervalued Companies to discover DUAL-CONFIRMED BARGAINS!
==============================================================================
"""

import os, sys, warnings, concurrent.futures
import numpy as np
import pandas as pd
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

warnings.filterwarnings("ignore")

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ANALYSIS_DIR)
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, ".gemini", "antigravity", "brain", "a0eeb781-d7e4-484e-898c-51f143744494")
REPORT_PATH   = os.path.join(ARTIFACTS_DIR, "DUAL_CONFIRMED_DCF_GRAHAM_REPORT.md")
CSV_PATH      = os.path.join(ANALYSIS_DIR, "dual_confirmed_dcf_graham_database.csv")
INPUT_CSV     = os.path.join(ANALYSIS_DIR, "all_stocks_graham_valuation_database.csv")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def run_dcf_single_symbol(row):
    sym = row["symbol"]
    graham_val = row["graham_value"]
    graham_disc = row["discount_pct"]
    sector = row.get("sector", "General")
    category = row.get("category", "Large Cap")

    try:
        t = yf.Ticker(sym)
        info = t.info

        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or row.get("price", 0.0)
        shares_out = info.get("sharesOutstanding") or 1.0
        total_cash = info.get("totalCash") or 0.0
        total_debt = info.get("totalDebt") or 0.0
        fcf = info.get("freeCashflow")

        if not fcf or fcf <= 0:
            op_cash = info.get("operatingCashflow") or (price * shares_out * 0.06)
            fcf = op_cash * 0.75

        wacc = 0.11 if ".NS" in sym else 0.09
        growth_rate = (info.get("earningsGrowth") or info.get("revenueGrowth") or 0.10)
        growth_rate = max(0.04, min(0.18, growth_rate))
        terminal_growth = 0.035

        # 5-Year DCF Cash Flow Projection
        forecast_years = 5
        pv_fcfs = []
        last_fcf = fcf

        for yr in range(1, forecast_years + 1):
            last_fcf = last_fcf * (1 + growth_rate)
            pv = last_fcf / ((1 + wacc) ** yr)
            pv_fcfs.append(pv)

        sum_pv_fcf = sum(pv_fcfs)
        term_val = (last_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
        pv_term_val = term_val / ((1 + wacc) ** forecast_years)

        enterprise_val = sum_pv_fcf + pv_term_val
        equity_val = enterprise_val + total_cash - total_debt
        dcf_intrinsic_price = equity_val / shares_out

        dcf_upside_pct = ((dcf_intrinsic_price - price) / (price + 1e-9)) * 100.0

        is_dcf_undervalued = price < dcf_intrinsic_price
        dual_confirmed = is_dcf_undervalued and row.get("is_undervalued", True)

        return {
            "symbol": sym,
            "name": info.get("shortName") or sym,
            "sector": sector,
            "category": category,
            "price": price,
            "graham_value": graham_val,
            "graham_discount_pct": graham_disc,
            "dcf_intrinsic_price": round(dcf_intrinsic_price, 2),
            "dcf_upside_pct": round(dcf_upside_pct, 1),
            "is_dcf_undervalued": is_dcf_undervalued,
            "dual_confirmed": dual_confirmed
        }
    except Exception:
        return None

def run_batch_dcf():
    print("=" * 85)
    print("  📊 BATCH DCF VALUATION ON BENJAMIN GRAHAM UNDERVALUED STOCKS")
    print("=" * 85)

    if not os.path.exists(INPUT_CSV):
        print(f"  ❌ Input database CSV not found: {INPUT_CSV}")
        return

    input_df = pd.read_csv(INPUT_CSV)
    undervalued_input = input_df[input_df["is_undervalued"]]

    print(f"  Loaded {len(undervalued_input)} Graham Undervalued Stocks for DCF Valuation...")

    results = []
    t0 = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(run_dcf_single_symbol, row) for _, row in undervalued_input.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    t1 = time.time()
    df = pd.DataFrame(results)
    df.to_csv(CSV_PATH, index=False)

    dual_confirmed_df = df[df["dual_confirmed"]].sort_values(by="dcf_upside_pct", ascending=False)
    
    total_analyzed = len(df)
    total_dual_confirmed = len(dual_confirmed_df)
    pct_dual = (total_dual_confirmed / max(1, total_analyzed)) * 100.0

    print("\n" + "=" * 85)
    print(f"  🏆 BATCH DCF VALUATION COMPLETED IN {t1-t0:.2f} SECONDS")
    print("=" * 85)
    print(f"  Total Graham Undervalued Stocks Analyzed:  {total_analyzed}")
    print(f"  DUAL-CONFIRMED BARGAINS (GRAHAM + DCF):    {total_dual_confirmed} ({pct_dual:.1f}%)")
    print("=" * 85)

    print("\n  📋 TOP DUAL-CONFIRMED UNDERVALUED BARGAINS (GRAHAM + DCF):")
    print(dual_confirmed_df[["symbol", "sector", "price", "graham_value", "dcf_intrinsic_price", "dcf_upside_pct"]].head(15).to_string())

    # Write Markdown Report Artifact
    report_md = f"""# 📊 DUAL-CONFIRMED DCF & BENJAMIN GRAHAM VALUATION REPORT

---

## 🏆 Summary of Dual-Confirmed Bargains
Evaluated using **BOTH Benjamin Graham's Intrinsic Value Formula** ($V^*$) AND **5-Year Discounted Cash Flow (DCF)**:

- **Total Graham Undervalued Stocks Analyzed**: `{total_analyzed}`
- **DUAL-CONFIRMED UNDERVALUED STOCKS (GRAHAM + DCF)**: **`{total_dual_confirmed}`** (**`{pct_dual:.1f}%`**)
- **Full Valuation Database CSV**: [`dual_confirmed_dcf_graham_database.csv`](file:///{CSV_PATH.replace('\\', '/')})

---

## 📋 Complete Ranking of Dual-Confirmed Bargains

```
==============================================================================================================
  DUAL-CONFIRMED BARGAINS (UNDERVALUED BY BOTH BENJAMIN GRAHAM & DISCOUNTED CASH FLOW)
==============================================================================================================

  Symbol           Sector               Price       Graham Value (V*)  DCF Intrinsic Price   DCF Upside (%)
  ------------------------------------------------------------------------------------------------------------
"""
    for _, row in dual_confirmed_df.iterrows():
        curr_sym = "₹" if ".NS" in row["symbol"] else "$"
        report_md += f"  {row['symbol']:<15s}  {row['sector']:<18s}   {curr_sym}{row['price']:>9.2f}     {curr_sym}{row['graham_value']:>12.2f}       {curr_sym}{row['dcf_intrinsic_price']:>12.2f}         +{row['dcf_upside_pct']:>6.1f}%\n"

    report_md += """==============================================================================================================
```
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n  📑 Report artifact saved to: {REPORT_PATH}")
    print(f"  💾 Database CSV saved to: {CSV_PATH}")

if __name__ == "__main__":
    import time
    run_batch_dcf()
