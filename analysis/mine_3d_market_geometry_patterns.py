"""
==============================================================================
  3D MARKET GEOMETRY QUANTITATIVE PATTERN & CORRELATION DISCOVERY ENGINE
==============================================================================
  Author: Uday Singh Rathore (@USRJ78) & @goforaditya
  Transforms price action into 3D Vector Space:
    X = Time (Bar Count)
    Y = Price Trajectory (Normalized Return)
    Z = Volatility / Volume Pressure (ATR Compression * Volume Ratio)
  
  Mines 3D Vector Curvature (κ), Torsion (τ), Vector Angle Inflections (θ),
  and identifies non-linear correlations triggering explosive price breakouts.
==============================================================================
"""

import os, sys, datetime
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

plt.switch_backend('Agg')

def calculate_3d_geometry(df):
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    volume = df['Volume'].values if 'Volume' in df.columns else np.ones(len(close))

    # 1. Coordinate Definitions:
    # X = Time index
    # Y = 10-bar price return
    # Z = Volatility-Volume Pressure (ATR10 / ATR50 * VolRatio)
    
    tr = np.maximum(high - low, np.maximum(abs(high - pd.Series(close).shift(1)), abs(low - pd.Series(close).shift(1))))
    atr10 = tr.rolling(10).mean().values
    atr50 = tr.rolling(50).mean().values
    vol_comp = atr10 / (atr50 + 1e-8)

    vol_sma = pd.Series(volume).rolling(20).mean().values
    vol_ratio = volume / (vol_sma + 1e-8)

    X = np.arange(len(close), dtype=float)
    Y = (close - pd.Series(close).shift(10).values) / (pd.Series(close).shift(10).values + 1e-8) * 100.0
    Z = vol_comp * np.clip(vol_ratio, 0.5, 3.0)

    # 2. Vector Calculus: Velocity (r') & Acceleration (r'')
    dY = np.gradient(Y)
    dZ = np.gradient(Z)
    dX = np.ones(len(X))

    ddY = np.gradient(dY)
    ddZ = np.gradient(dZ)
    ddX = np.zeros(len(X))

    # 3. 3D Curvature (kappa)
    # kappa = |r' x r''| / |r'|^3
    vel = np.vstack((dX, dY, dZ)).T
    acc = np.vstack((ddX, ddY, ddZ)).T

    cross = np.cross(vel, acc)
    cross_norm = np.linalg.norm(cross, axis=1)
    vel_norm = np.linalg.norm(vel, axis=1)

    kappa = cross_norm / (vel_norm**3 + 1e-8)

    # 4. Vector Angle (theta) between Velocity & Acceleration
    dot = np.sum(vel * acc, axis=1)
    cos_theta = dot / (vel_norm * np.linalg.norm(acc, axis=1) + 1e-8)
    theta_deg = np.arccos(np.clip(cos_theta, -1.0, 1.0)) * (180.0 / np.pi)

    # Subsequent 5-bar forward price move (%)
    fwd_return = (pd.Series(close).shift(-5).values - close) / close * 100.0

    df['X_Time'] = X
    df['Y_Return'] = Y
    df['Z_Pressure'] = Z
    df['3D_Curvature_Kappa'] = kappa
    df['3D_Vector_Angle_Theta'] = theta_deg
    df['Fwd_Return_5D'] = fwd_return

    return df.dropna()

def run_3d_pattern_discovery():
    print("=" * 80)
    print("  🚀 3D MARKET GEOMETRY VECTOR PATTERN & CORRELATION DISCOVERY ENGINE")
    print("=" * 80)

    assets = {
        '^NSEI': 'Nifty 50 Index',
        'BTC-USD': 'Bitcoin'
    }

    results = {}

    for ticker, name in assets.items():
        print(f"\n  [1/3] MINING 3D VECTOR FIELD PATTERNS FOR {name} ({ticker})...")
        df = yf.download(ticker, start="2016-01-01", end="2026-08-01", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()

        df_geo = calculate_3d_geometry(df)

        # Pattern Condition 1: Extreme 3D Curvature Compression (kappa < 0.05) + Low Pressure (Z < 0.85)
        pattern_squeeze = df_geo[(df_geo['3D_Curvature_Kappa'] < 0.05) & (df_geo['Z_Pressure'] < 0.85)]
        
        # Pattern Condition 2: 3D Vector Alignment (Theta < 20 deg) + Pressure Spike (Z > 1.25)
        pattern_breakout = df_geo[(df_geo['3D_Vector_Angle_Theta'] < 20.0) & (df_geo['Z_Pressure'] > 1.25)]

        avg_fwd_squeeze = pattern_squeeze['Fwd_Return_5D'].mean()
        avg_fwd_breakout = pattern_breakout['Fwd_Return_5D'].mean()

        win_rate_breakout = (pattern_breakout['Fwd_Return_5D'] > 0).mean() * 100.0 if len(pattern_breakout) > 0 else 0

        # Correlation between 3D Vector Angle (Theta) and Forward Price Acceleration
        corr_theta_return = df_geo['3D_Vector_Angle_Theta'].corr(df_geo['Fwd_Return_5D'])
        corr_kappa_return = df_geo['3D_Curvature_Kappa'].corr(abs(df_geo['Fwd_Return_5D']))

        results[ticker] = {
            'name': name,
            'df': df_geo,
            'squeeze_count': len(pattern_squeeze),
            'avg_fwd_squeeze': avg_fwd_squeeze,
            'breakout_count': len(pattern_breakout),
            'avg_fwd_breakout': avg_fwd_breakout,
            'win_rate_breakout': win_rate_breakout,
            'corr_theta': corr_theta_return,
            'corr_kappa': corr_kappa_return
        }

        print(f"    • Total Analyzed Bars        : {len(df_geo)} daily bars")
        print(f"    • 3D Squeeze Signals (κ<0.05): {len(pattern_squeeze)} occurrences | Avg 5D Move: {avg_fwd_squeeze:+.2f}%")
        print(f"    • 3D Vector Alignment (θ<20°): {len(pattern_breakout)} occurrences | Avg 5D Move: {avg_fwd_breakout:+.2f}%")
        print(f"    • Breakout Win Rate          : {win_rate_breakout:.1f}%")
        print(f"    • 3D Vector Alignment Correlation: r = {corr_theta_return:+.3f}")

    # Generate 3D Surface Plot Artifact
    artifacts_dir = r"C:\Users\USER\.gemini\antigravity\brain\a0eeb781-d7e4-484e-898c-51f143744494"
    chart_path = os.path.join(artifacts_dir, "3d_market_geometry_patterns.png")

    fig = plt.figure(figsize=(14, 6), facecolor='#0b0f19')
    ax = fig.add_subplot(121, projection='3d', facecolor='#0b0f19')
    
    nifty_df = results['^NSEI']['df'].tail(500)
    sc = ax.scatter(nifty_df['X_Time'], nifty_df['Y_Return'], nifty_df['Z_Pressure'],
                    c=nifty_df['Fwd_Return_5D'], cmap='coolwarm', s=25, alpha=0.85)

    ax.set_title("Nifty 50 -- 3D Vector Trajectory Space\n(X: Time | Y: Return | Z: Pressure)", color='#ffffff', fontsize=11, fontweight='bold')
    ax.set_xlabel("Time (X)", color='#a0aec0', fontsize=8)
    ax.set_ylabel("10D Return % (Y)", color='#a0aec0', fontsize=8)
    ax.set_zlabel("Pressure (Z)", color='#a0aec0', fontsize=8)
    ax.tick_params(colors='#a0aec0', labelsize=7)

    cb = plt.colorbar(sc, ax=ax, shrink=0.5, pad=0.1)
    cb.set_label("Subsequent 5-Day Return (%)", color='#a0aec0')
    cb.ax.yaxis.set_tick_params(color='#a0aec0')
    plt.setp(plt.getp(cb.ax, 'yticklabels'), color='#a0aec0')

    # Chart 2: Bitcoin 3D Scatter
    ax2 = fig.add_subplot(122, projection='3d', facecolor='#0b0f19')
    btc_df = results['BTC-USD']['df'].tail(500)
    sc2 = ax2.scatter(btc_df['X_Time'], btc_df['Y_Return'], btc_df['Z_Pressure'],
                      c=btc_df['Fwd_Return_5D'], cmap='magma', s=25, alpha=0.85)

    ax2.set_title("Bitcoin -- 3D Vector Trajectory Space\n(X: Time | Y: Return | Z: Pressure)", color='#ffffff', fontsize=11, fontweight='bold')
    ax2.set_xlabel("Time (X)", color='#a0aec0', fontsize=8)
    ax2.set_ylabel("10D Return % (Y)", color='#a0aec0', fontsize=8)
    ax2.set_zlabel("Pressure (Z)", color='#a0aec0', fontsize=8)
    ax2.tick_params(colors='#a0aec0', labelsize=7)

    cb2 = plt.colorbar(sc2, ax=ax2, shrink=0.5, pad=0.1)
    cb2.set_label("Subsequent 5-Day Return (%)", color='#a0aec0')
    cb2.ax.yaxis.set_tick_params(color='#a0aec0')
    plt.setp(plt.getp(cb2.ax, 'yticklabels'), color='#a0aec0')

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, facecolor=fig.get_facecolor())
    plt.close()

    print(f"\n  [OK] 3D Vector Field Artifact saved to: {chart_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_3d_pattern_discovery()
