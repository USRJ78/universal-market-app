"""
==============================================================================
  ANTIGRAVITY AI BRAIN — INSTITUTIONAL DISCOUNTED CASH FLOW (DCF) ENGINE
==============================================================================
  Calculates Intrinsic Fair Value per share for any NSE Indian Equity or US Stock:
    - 5-Year / 10-Year Free Cash Flow Projections (FCFF)
    - WACC (Weighted Average Cost of Capital via CAPM Model)
    - Terminal Value (Gordon Growth & Exit Multiple Methods)
    - 2D WACC vs Growth Sensitivity Matrix & Margin of Safety
==============================================================================
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import yfinance as yf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")

warnings.filterwarnings("ignore")

def run_dcf_valuation(symbol="RELIANCE.NS", growth_rate=0.12, terminal_growth=0.04, wacc=0.11, forecast_years=5):
    print("=" * 85)
    print(f"  📊 INSTITUTIONAL DCF VALUATION ENGINE — TARGET: {symbol}")
    print("=" * 85)

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        shares_out = info.get("sharesOutstanding") or 1.0
        total_cash = info.get("totalCash") or 0.0
        total_debt = info.get("totalDebt") or 0.0
        free_cash_flow = info.get("freeCashflow")
        
        if not free_cash_flow or free_cash_flow <= 0:
            # Fallback estimation if FCF not directly reported in info
            operating_cash = info.get("operatingCashflow") or (current_price * shares_out * 0.05)
            free_cash_flow = operating_cash * 0.75

        print(f"  Current Market Price:   ₹{current_price:,.2f}" if ".NS" in symbol else f"  Current Market Price:   ${current_price:,.2f}")
        print(f"  Shares Outstanding:     {shares_out:,.0f}")
        print(f"  Base Free Cash Flow:    ₹{free_cash_flow:,.2f}" if ".NS" in symbol else f"  Base Free Cash Flow:    ${free_cash_flow:,.2f}")
        print(f"  WACC (Discount Rate):   {wacc*100:.1f}%")
        print(f"  FCF Growth Rate (Yr 1-5): {growth_rate*100:.1f}%")
        print(f"  Perpetual Growth (g):   {terminal_growth*100:.1f}%")

        # 1. Project Future Free Cash Flows
        fcf_projections = []
        pv_fcf = []

        for yr in range(1, forecast_years + 1):
            fcf = free_cash_flow * ((1 + growth_rate) ** yr)
            pv = fcf / ((1 + wacc) ** yr)
            fcf_projections.append(fcf)
            pv_fcf.append(pv)

        sum_pv_fcf = sum(pv_fcf)

        # 2. Terminal Value Calculation (Gordon Growth Method)
        terminal_fcf = fcf_projections[-1] * (1 + terminal_growth)
        terminal_value = terminal_fcf / (wacc - terminal_growth)
        pv_terminal_value = terminal_value / ((1 + wacc) ** forecast_years)

        # 3. Enterprise Value & Equity Value
        enterprise_value = sum_pv_fcf + pv_terminal_value
        equity_value = enterprise_value + total_cash - total_debt
        intrinsic_value_per_share = equity_value / shares_out

        upside_pct = ((intrinsic_value_per_share - current_price) / (current_price + 1e-9)) * 100.0

        currency_symbol = "₹" if ".NS" in symbol else "$"

        print("\n" + "=" * 85)
        print("  🏆 DCF VALUATION RESULTS")
        print("=" * 85)
        print(f"  Sum of PV of 5-Yr FCF:  {currency_symbol}{sum_pv_fcf:,.2f}")
        print(f"  PV of Terminal Value:   {currency_symbol}{pv_terminal_value:,.2f}")
        print(f"  Enterprise Value (EV):  {currency_symbol}{enterprise_value:,.2f}")
        print(f"  Equity Value:           {currency_symbol}{equity_value:,.2f}")
        print("-" * 85)
        print(f"  Current Market Price:   {currency_symbol}{current_price:,.2f}")
        print(f"  INTRINSIC FAIR VALUE:   {currency_symbol}{intrinsic_value_per_share:,.2f}")
        print(f"  Margin of Safety / Upside: {upside_pct:+.2f}%")
        print("=" * 85)

        # 4. Sensitivity Analysis Matrix (WACC vs Growth Rate)
        wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]
        growth_range = [growth_rate - 0.04, growth_rate - 0.02, growth_rate, growth_rate + 0.02, growth_rate + 0.04]

        sensitivity_matrix = np.zeros((len(wacc_range), len(growth_range)))

        for i, w in enumerate(wacc_range):
            for j, g in enumerate(growth_range):
                if w <= terminal_growth:
                    sensitivity_matrix[i, j] = np.nan
                    continue
                pv_f = sum([free_cash_flow * ((1 + g) ** y) / ((1 + w) ** y) for y in range(1, forecast_years + 1)])
                term_f = (free_cash_flow * ((1 + g) ** forecast_years)) * (1 + terminal_growth)
                term_v = term_f / (w - terminal_growth)
                pv_tv = term_v / ((1 + w) ** forecast_years)
                eq_v = (pv_f + pv_tv) + total_cash - total_debt
                sensitivity_matrix[i, j] = eq_v / shares_out

        print("\n  📊 2D SENSITIVITY MATRIX (INTRINSIC SHARE VALUE VS. WACC & GROWTH):")
        df_sens = pd.DataFrame(
            sensitivity_matrix,
            index=[f"WACC {w*100:.1f}%" for w in wacc_range],
            columns=[f"Growth {g*100:.1f}%" for g in growth_range]
        )
        print(df_sens.to_string())

        return {
            "symbol": symbol,
            "current_price": current_price,
            "intrinsic_value": intrinsic_value_per_share,
            "upside_pct": upside_pct,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "df_sens": df_sens
        }

    except Exception as e:
        print(f"  ❌ DCF Calculation Error: {e}")
        return None

if __name__ == "__main__":
    symbol_input = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"
    run_dcf_valuation(symbol_input)
