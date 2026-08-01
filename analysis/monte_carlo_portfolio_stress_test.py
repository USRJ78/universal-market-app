"""
==============================================================================
  10,000-RUN MONTE CARLO PORTFOLIO TAIL-RISK STRESS TEST ENGINE
  TESTING BLACK SWAN SHOCKS & VALUE-AT-RISK (VaR 99%)
==============================================================================
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_monte_carlo_simulation(initial_cap=100000.0, num_sims=10000, num_days=252):
    print("=" * 75)
    print("  10,000-RUN MONTE CARLO PORTFOLIO STRESS TEST ENGINE")
    print("=" * 75)

    np.random.seed(42)

    # Strategy Parameters (Ouroboros V6.0 / Swarm Alpha Engine)
    daily_mu = 0.0584 / 252.0  # Daily drift (5.84% CAGR)
    daily_vol = 0.08 / np.sqrt(252) # Low Volatility due to 1x2 Ratio Spreads

    # Generate 10,000 Price Trajectories using Geometric Brownian Motion + Fat-Tail Jump Diffusion
    dt = 1 / 252.0
    sim_matrix = np.zeros((num_sims, num_days + 1))
    sim_matrix[:, 0] = initial_cap

    for t in range(1, num_days + 1):
        # Jump Diffusion (Black Swan crash event 2% probability of -5% jump)
        z = np.random.standard_normal(num_sims)
        jumps = (np.random.rand(num_sims) < 0.02) * (np.random.uniform(-0.05, -0.02, num_sims))
        
        daily_ret = np.exp((daily_mu - 0.5 * daily_vol**2) * dt + daily_vol * np.sqrt(dt) * z) - 1.0 + jumps
        sim_matrix[:, t] = sim_matrix[:, t - 1] * (1.0 + daily_ret)

    final_equities = sim_matrix[:, -1]
    
    mean_equity = np.mean(final_equities)
    median_equity = np.median(final_equities)
    var_95 = np.percentile(final_equities, 5)
    var_99 = np.percentile(final_equities, 1)
    max_sim_equity = np.max(final_equities)
    min_sim_equity = np.min(final_equities)

    print(f"  Total Simulations    : {num_sims:,}")
    print(f"  Starting Capital     : ${initial_cap:,.2f} USD")
    print(f"  Expected Mean Equity : ${mean_equity:,.2f} USD")
    print(f"  Median Equity        : ${median_equity:,.2f} USD")
    print(f"  95% Value-at-Risk    : ${var_95:,.2f} USD (Max Expected Loss: ${initial_cap - var_95:,.2f})")
    print(f"  99% Value-at-Risk    : ${var_99:,.2f} USD (Max Expected Loss: ${initial_cap - var_99:,.2f})")
    print(f"  Best Case Simulation : ${max_sim_equity:,.2f} USD")
    print(f"  Worst Case Crash     : ${min_sim_equity:,.2f} USD")
    print("=" * 75)

    # Plot Monte Carlo Distribution
    plot_monte_carlo(sim_matrix, var_95, var_99, initial_cap)

    return {
        "Mean": mean_equity,
        "Median": median_equity,
        "VaR_95": var_95,
        "VaR_99": var_99,
        "Min": min_sim_equity,
        "Max": max_sim_equity
    }


def plot_monte_carlo(sim_matrix, var_95, var_99, initial_cap):
    p = {"bg": "#0d1117", "panel": "#161b22", "cyan": "#00ffcc", "red": "#f85149", "gold": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(p["bg"])
    ax.set_facecolor(p["panel"])

    # Plot top 100 sample trajectories
    time_steps = np.arange(sim_matrix.shape[1])
    for i in range(100):
        ax.plot(time_steps, sim_matrix[i], color=p["cyan"], alpha=0.08, lw=0.8)

    # Median Trajectory
    med = np.median(sim_matrix, axis=0)
    ax.plot(time_steps, med, color=p["gold"], lw=2.5, label="Median Trajectory")

    # VaR 99 Boundary
    ax.axhline(var_99, color=p["red"], ls="--", lw=1.8, label=f"99% VaR Boundary (${var_99:,.0f})")

    ax.set_title("10,000-Run Monte Carlo Simulation: 1-Year Stress Test & Jump-Diffusion Risk", color=p["text"], fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Trading Days", color=p["muted"])
    ax.set_ylabel("Portfolio Equity ($ USD)", color=p["muted"])
    ax.tick_params(colors=p["muted"])
    ax.grid(True, color="#30363d", ls=":", alpha=0.5)
    ax.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

    out_png = os.path.join(OUTPUT_DIR, "monte_carlo_stress_chart.png")
    plt.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=p["bg"])
    plt.close()
    print(f"[OK] Monte Carlo Stress Test Chart saved -> {out_png}")


if __name__ == "__main__":
    run_monte_carlo_simulation()
