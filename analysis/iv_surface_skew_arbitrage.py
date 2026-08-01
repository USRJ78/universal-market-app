"""
==============================================================================
  BLACK-SCHOLES VOLATILITY SURFACE & IV SKEW ARBITRAGE ENGINE
  QUANTITATIVE MODEL FOR OPTIONS MISPRICING & NON-LINEAR CONVEXITY
==============================================================================
"""

import os, sys, math
import numpy as np
import pandas as pd
from scipy.stats import norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Black-Scholes Formulae
def bs_call_price(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def bs_greeks(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return {"delta": 1.0 if S > K else 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    delta = norm.cdf(d1)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100.0  # per 1% change in IV
    theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365.0
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def scan_iv_skew_arbitrage(spot=65000.0, r=0.05, base_iv=0.55):
    print("=" * 75)
    print("  BLACK-SCHOLES VOLATILITY SURFACE & IV SKEW ARBITRAGE ENGINE")
    print("=" * 75)

    strikes = np.linspace(spot * 0.85, spot * 1.20, 15)
    expiry_days = [7, 14, 30, 45, 60]

    matrix_results = []

    for days in expiry_days:
        T = days / 365.0
        for K in strikes:
            # Volatility Skew Model (Volatility Smile: higher IV for OTM Puts and OTM Calls)
            moneyness = np.log(K / spot)
            skew_iv = base_iv + 0.25 * (moneyness ** 2) - 0.10 * moneyness
            
            call_price = bs_call_price(spot, K, T, r, skew_iv)
            greeks = bs_greeks(spot, K, T, r, skew_iv)

            # 1x2 Ratio Call Spread pricing: Buy 1x ATM (K1), Sell 2x OTM (K2)
            k1_price = bs_call_price(spot, spot, T, r, base_iv)
            k2_price = bs_call_price(spot, spot * 1.045, T, r, skew_iv)
            net_debit = k1_price - 2 * k2_price

            matrix_results.append({
                "Expiry_Days": days,
                "Strike_K": round(K, 2),
                "Moneyness_%": round((K / spot - 1) * 100, 2),
                "Implied_Vol_%": round(skew_iv * 100, 2),
                "Call_Price_$": round(call_price, 2),
                "Delta": round(greeks["delta"], 4),
                "Gamma": round(greeks["gamma"], 6),
                "Vega": round(greeks["vega"], 4),
                "Theta": round(greeks["theta"], 4),
                "1x2_Net_Debit_$": round(net_debit, 2)
            })

    df = pd.DataFrame(matrix_results)
    out_csv = os.path.join(OUTPUT_DIR, "iv_surface_skew_results.csv")
    df.to_csv(out_csv, index=False)
    print(f"\n[OK] Volatility Surface Skew Matrix saved -> {out_csv}")

    # Plot Volatility Surface
    plot_iv_surface(df, spot)
    return df


def plot_iv_surface(df, spot):
    p = {"bg": "#0d1117", "panel": "#161b22", "cyan": "#00ffcc", "gold": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig = plt.figure(figsize=(12, 6))
    fig.patch.set_facecolor(p["bg"])
    ax = fig.add_subplot(111)
    ax.set_facecolor(p["panel"])

    for days, group in df.groupby("Expiry_Days"):
        ax.plot(group["Moneyness_%"], group["Implied_Vol_%"], marker="o", label=f"Expiry: {days} Days")

    ax.set_title(f"Black-Scholes Volatility Skew Smile Curve (Spot: ${spot:,.0f})", color=p["text"], fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Moneyness (% distance from ATM)", color=p["muted"])
    ax.set_ylabel("Implied Volatility (IV %)", color=p["muted"])
    ax.tick_params(colors=p["muted"])
    ax.grid(True, color="#30363d", ls=":", alpha=0.5)
    ax.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    out_png = os.path.join(OUTPUT_DIR, "iv_surface_skew_chart.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] IV Skew Surface Chart saved -> {out_png}")


if __name__ == "__main__":
    scan_iv_skew_arbitrage()
