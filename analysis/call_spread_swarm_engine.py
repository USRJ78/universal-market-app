"""
==============================================================================
  AUTONOMOUS SWARM BOT ENGINE FOR CALL SPREAD POSITION DISCOVERY
==============================================================================

SWARM BOT ARCHITECTURE:
  1. AGENT ALPHA (Kinetic Momentum Hunter):
     Scans 52-Week High Breakouts, 20-Day High Expansion, & EMA 20/50 Trend.

  2. AGENT BETA (Volatility Compression Hunter):
     Scans ATR Squeezes (ATR10/ATR50 < 0.90), Bollinger Band Compression, & IV.

  3. AGENT GAMMA (Option Geometry Optimizer):
     Calculates Black-Scholes strike matrices to find Zero-Debit 1x2 Ratio Spreads.

  4. AGENT DELTA (Swarm Allocator & Risk Controller):
     Aggregates multi-agent signals, ranks candidate positions, and outputs an
     actionable Call Spread Execution Matrix!

OUTPUTS:
  - call_spread_swarm_report.md
  - call_spread_swarm_candidates.csv
  - call_spread_swarm_chart.png
==============================================================================
"""

import os, sys, time, json, warnings, datetime, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from scipy.stats import norm

# Force stdout to unbuffered line-buffering mode so logs appear instantly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

warnings.filterwarnings("ignore")

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUTPUT_DIR, "swarm_execution.log")
LOG_FILE_ALT = os.path.join(OUTPUT_DIR, "swarm_call_spread.log")
BRAIN_STATE_FILE = os.path.join(OUTPUT_DIR, "../antigravity_ai_brain/ai_brain_state.json")

def log_print(msg="", to_file=True):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [SWARM-BOT] {msg}" if not str(msg).startswith("[") and not str(msg).startswith("=") else str(msg)
    print(formatted, flush=True)
    if to_file:
        for lpath in [LOG_FILE, LOG_FILE_ALT]:
            try:
                with open(lpath, "a", encoding="utf-8") as f:
                    f.write(formatted + "\n")
            except Exception:
                pass


# Multi-Asset Futures & Options Universe
SWARM_UNIVERSE = [
    # Index Futures
    "^NSEI",          # Nifty 50
    "^NSEBANK",       # Bank Nifty
    "BTC-USD",        # Bitcoin Crypto
    "ETH-USD",        # Ethereum Crypto
    
    # High-Beta Futures & Momentum Stocks
    "ANANTRAJ.NS", "AIIL.NS", "ABB.NS", "ABREL.NS", "ANANDRATHI.NS",
    "RELIANCE.NS", "BHARTIARTL.NS", "INFY.NS", "TITAN.NS",
    "TATASTEEL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "SBIN.NS",
    "LT.NS", "BAJFINANCE.NS", "TCS.NS", "NTPC.NS", "POWERGRID.NS"
]


# ─────────────────────────────────────────────
# AGENT ALPHA: KINETIC MOMENTUM HUNTER
# ─────────────────────────────────────────────
class KineticMomentumAgent:
    def evaluate(self, df):
        close = df["Close"]
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        high52 = close.rolling(252).max()
        high20 = close.rolling(20).max()

        last_close = float(close.iloc[-1])
        last_ema20 = float(ema20.iloc[-1])
        last_ema50 = float(ema50.iloc[-1])
        last_h52   = float(high52.iloc[-1])
        last_h20   = float(high20.iloc[-1])

        trend_score = 1.0 if (last_close > last_ema20 > last_ema50) else 0.5 if (last_close > last_ema50) else 0.0
        breakout_score = 1.0 if (last_close >= last_h52 * 0.98) else 0.7 if (last_close >= last_h20 * 0.98) else 0.2

        composite_score = (0.6 * trend_score) + (0.4 * breakout_score)
        return composite_score, last_close, last_h52


# ─────────────────────────────────────────────
# AGENT BETA: VOLATILITY COMPRESSION HUNTER
# ─────────────────────────────────────────────
class VolatilityCompressionAgent:
    def evaluate(self, df):
        hl = df["High"] - df["Low"]
        hc = (df["High"] - df["Close"].shift()).abs()
        lc = (df["Low"] - df["Close"].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)

        atr10 = tr.rolling(10).mean()
        atr50 = tr.rolling(50).mean()
        sqz   = atr10 / (atr50 + 1e-9)

        last_sqz = float(sqz.iloc[-1])
        
        # Historical Volatility (20-day annualized)
        log_ret = np.log(df["Close"] / df["Close"].shift(1))
        hv20 = float(log_ret.rolling(20).std().iloc[-1] * np.sqrt(252))

        # Higher squeeze score when ATR ratio < 0.92
        squeeze_score = 1.0 if (last_sqz < 0.88) else 0.8 if (last_sqz < 0.95) else 0.3
        return squeeze_score, last_sqz, hv20


# ─────────────────────────────────────────────
# AGENT GAMMA: OPTION GEOMETRY OPTIMIZER
# ─────────────────────────────────────────────
class OptionGeometryAgent:
    def calculate_bs_call(self, S, K, T, r, sigma):
        if T <= 0 or sigma <= 0: return max(S - K, 0)
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))

    def optimize_spread(self, S, hv, dte=30, r=0.065):
        T = dte / 365.0
        sigma = max(hv, 0.15)  # Minimum 15% IV

        # K1 = ATM Strike
        step = 50 if S > 10000 else 10 if S > 1000 else 5 if S > 100 else 1
        k1 = round(S / step) * step
        
        # Find K2 for Zero-Debit 1x2 Ratio Spread (1x K1 Call - 2x K2 Call ~ 0)
        c1 = self.calculate_bs_call(S, k1, T, r, sigma)
        
        best_k2 = k1 + step
        best_debit_diff = 999999
        best_debit = c1

        for k2_candidate in np.arange(k1 + step, k1 * 1.15, step):
            c2 = self.calculate_bs_call(S, k2_candidate, T, r, sigma)
            debit = c1 - 2 * c2
            if abs(debit) < best_debit_diff:
                best_debit_diff = abs(debit)
                best_k2 = k2_candidate
                best_debit = debit

        c2_best = self.calculate_bs_call(S, best_k2, T, r, sigma)
        max_payoff_at_k2 = (best_k2 - k1) - max(best_debit, 0)
        return k1, best_k2, c1, c2_best, best_debit, max_payoff_at_k2


# ─────────────────────────────────────────────
# AGENT DELTA: SWARM ALLOCATOR & OVERSEER
# ─────────────────────────────────────────────
class SwarmOverseer:
    def __init__(self):
        self.agent_alpha = KineticMomentumAgent()
        self.agent_beta  = VolatilityCompressionAgent()
        self.agent_gamma = OptionGeometryAgent()

    def run_swarm_scan(self, active_pid=None):
        log_print("=" * 75)
        log_print("  AUTONOMOUS CALL SPREAD SWARM BOT ENGINE — SCAN ACTIVE")
        log_print("=" * 75)

        results = []
        log_print(f"[1] SWARM AGENTS SCANNING {len(SWARM_UNIVERSE)} ASSETS ...")

        for ticker in SWARM_UNIVERSE:
            try:
                df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
                if df is None or len(df) < 50 or df.empty:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # Agent Evaluations
                m_score, S, high52 = self.agent_alpha.evaluate(df)
                v_score, sqz, hv20 = self.agent_beta.evaluate(df)

                # Composite Swarm Score
                swarm_score = (0.55 * m_score) + (0.45 * v_score)

                # Option Geometry Optimization
                k1, k2, c1, c2, debit, max_payoff = self.agent_gamma.optimize_spread(S, hv20)

                results.append({
                    "Ticker": ticker.replace("^NSEI", "NIFTY50").replace("^NSEBANK", "BANKNIFTY"),
                    "Spot_Price": round(S, 2),
                    "52W_High": round(high52, 2),
                    "Swarm_Score": round(swarm_score * 100, 1),
                    "Momentum_Score": round(m_score * 100, 1),
                    "Squeeze_Ratio": round(sqz, 2),
                    "HV20_%": round(hv20 * 100, 1),
                    "K1_ATM_Strike": k1,
                    "K2_OTM_Strike": k2,
                    "K1_Call_Price": round(c1, 2),
                    "K2_Call_Price": round(c2, 2),
                    "Net_Debit": round(debit, 2),
                    "Max_Payoff_Spike": round(max_payoff, 2),
                    "High_Conviction": swarm_score >= 0.70
                })
                log_print(f"  [OK] Agent evaluated {ticker:12s} | Swarm Score: {swarm_score*100:.1f}/100")
            except Exception as e:
                pass

        if not results:
            log_print("[WARN] No market data retrieved in this scan pass.")
            return []

        df_res = pd.DataFrame(results).sort_values("Swarm_Score", ascending=False).reset_index(drop=True)

        log_print("\n" + "=" * 75)
        log_print("  TOP SWARM DISCOVERED CALL SPREAD POSITIONS")
        log_print("=" * 75)
        top_candidates = df_res[df_res["High_Conviction"]].head(8)
        log_print(top_candidates[["Ticker", "Spot_Price", "Swarm_Score", "K1_ATM_Strike", "K2_OTM_Strike", "Net_Debit", "Max_Payoff_Spike"]].to_string(index=False))

        # Save CSV
        out_csv = os.path.join(OUTPUT_DIR, "call_spread_swarm_candidates.csv")
        df_res.to_csv(out_csv, index=False)
        log_print(f"\n[OK] Candidates saved -> {out_csv}")

        # Plot Swarm Leaderboard & Report
        self.plot_swarm_results(df_res)
        self.generate_report(df_res)

        # Sync state with Antigravity AI Brain
        self.sync_brain_state(top_candidates, active_pid)

        return df_res.to_dict(orient="records")

    def sync_brain_state(self, top_df, active_pid):
        if not os.path.exists(BRAIN_STATE_FILE):
            return
        try:
            with open(BRAIN_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            state["is_running"] = True
            if active_pid:
                state["pid"] = int(active_pid)
            state["active_strategy"] = "🚀 Swarm Bot 1x2 Ratio Call Spread (Zero Debit)"
            state["last_update"] = datetime.datetime.now().isoformat()
            if not top_df.empty:
                top_row = top_df.iloc[0]
                state["active_position"] = {
                    "strategy": "swarm_call_spread",
                    "ticker": str(top_row["Ticker"]),
                    "swarm_score": float(top_row["Swarm_Score"]),
                    "k1_strike": float(top_row["K1_ATM_Strike"]),
                    "k2_strike": float(top_row["K2_OTM_Strike"]),
                    "net_debit": float(top_row["Net_Debit"]),
                    "max_payoff": float(top_row["Max_Payoff_Spike"])
                }
            with open(BRAIN_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            log_print(f"[WARN] Error syncing brain state: {e}")

    def plot_swarm_results(self, df_res):
        p = {"bg": "#0d1117", "panel": "#161b22", "green": "#39d353", "red": "#f85149",
             "blue": "#58a6ff", "yellow": "#e3b341", "text": "#c9d1d9", "muted": "#8b949e"}

        fig = plt.figure(figsize=(16, 9))
        fig.patch.set_facecolor(p["bg"])
        gs = gridspec.GridSpec(2, 2, hspace=0.42, wspace=0.30)

        def sa(ax, title):
            ax.set_facecolor(p["panel"])
            ax.tick_params(colors=p["muted"], labelsize=9)
            ax.set_title(title, color=p["text"], fontsize=10, fontweight="bold", pad=10)
            for s in ax.spines.values():
                s.set_edgecolor("#30363d")

        # 1. Swarm Score Leaderboard
        ax1 = fig.add_subplot(gs[0, :])
        sa(ax1, "Swarm Bot Conviction Score by Asset (Top Candidate Setups)")
        top15 = df_res.head(12)
        cols  = [p["green"] if s >= 70 else p["yellow"] if s >= 50 else p["muted"] for s in top15["Swarm_Score"]]
        bars1 = ax1.bar(top15["Ticker"], top15["Swarm_Score"], color=cols, edgecolor="#30363d")
        for bar in bars1:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5, f"{bar.get_height():.1f}",
                     ha="center", fontsize=8, color=p["text"], fontweight="bold")
        ax1.axhline(70, color=p["green"], ls="--", lw=1.0, label="High Conviction Threshold (70+)")
        ax1.set_ylabel("Swarm Conviction Score (0-100)", color=p["muted"])
        ax1.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

        # 2. Net Debit vs Max Payoff Scatter
        ax2 = fig.add_subplot(gs[1, 0])
        sa(ax2, "1x2 Ratio Call Spread: Net Debit vs Max Payoff Spike")
        ax2.scatter(df_res["Net_Debit"], df_res["Max_Payoff_Spike"], color=p["blue"], s=70, alpha=0.8, edgecolors=p["text"])
        for _, r in df_res.head(5).iterrows():
            ax2.annotate(r["Ticker"], (r["Net_Debit"], r["Max_Payoff_Spike"]), color=p["yellow"], fontsize=8, xytext=(4, 4), textcoords="offset points")
        ax2.set_xlabel("Net Debit (Rs. / $)", color=p["muted"])
        ax2.set_ylabel("Max Payoff at K2", color=p["muted"])

        # 3. Volatility Squeeze vs Momentum Matrix
        ax3 = fig.add_subplot(gs[1, 1])
        sa(ax3, "Swarm Matrix: Momentum Score vs Vol Squeeze Ratio")
        sc = ax3.scatter(df_res["Momentum_Score"], df_res["Squeeze_Ratio"], c=df_res["Swarm_Score"], cmap="viridis", s=80)
        cbar = plt.colorbar(sc, ax=ax3)
        cbar.ax.tick_params(labelsize=8, labelcolor=p["muted"])
        ax3.set_xlabel("Momentum Score %", color=p["muted"])
        ax3.set_ylabel("Squeeze Ratio (ATR10/50)", color=p["muted"])
        ax3.axhline(0.92, color=p["red"], ls=":", label="Vol Squeeze Trigger (<0.92)")
        ax3.legend(facecolor=p["panel"], labelcolor=p["text"], edgecolor="#30363d")

        plt.suptitle("AUTONOMOUS SWARM BOT ENGINE  |  CALL SPREAD POSITION DISCOVERY",
                     color=p["text"], fontsize=12, fontweight="bold", y=0.99)

        out_chart = os.path.join(OUTPUT_DIR, "call_spread_swarm_chart.png")
        plt.savefig(out_chart, dpi=150, bbox_inches="tight", facecolor=p["bg"])
        plt.close()
        log_print(f"[OK] Swarm Chart saved -> {out_chart}")

    def generate_report(self, df_res):
        top = df_res[df_res["High_Conviction"]]
        out_chart = os.path.join(OUTPUT_DIR, "call_spread_swarm_chart.png")

        report_md = f"""# 🤖 Autonomous Swarm Bot Engine: Call Spread Positions

## 🎯 Swarm Multi-Agent Discovery Summary

Our **Multi-Agent Quant Swarm** scanned multi-asset futures & options markets (Nifty 50, Bank Nifty, Crypto, and High-Beta Momentum Stocks) to isolate high-conviction **1x2 Ratio Call Spread** setups.

---

### 📊 Top Swarm Discovered Positions

| Ticker | Spot Price | Swarm Score | ATM Call ($K_1$) | OTM Call ($K_2$) | Net Debit | Max Payoff Spike |
|---|---|---|---|---|---|---|
"""
        for _, r in top.iterrows():
            report_md += f"| **{r['Ticker']}** | {r['Spot_Price']} | **{r['Swarm_Score']}/100** | {r['K1_ATM_Strike']} | {r['K2_OTM_Strike']} | {r['Net_Debit']} | **+{r['Max_Payoff_Spike']}** |\n"

        report_md += f"""
---

### 🔑 The 4-Agent Swarm Logic

1. **Agent Alpha (Kinetic Momentum):** Evaluates 52-week breakout proximity & 20/50 EMA alignment.
2. **Agent Beta (Vol Compression):** Measures ATR squeeze ($\text{{ATR}}_{{10}} / \text{{ATR}}_{{50}} < 0.92$) & 20-day historical volatility.
3. **Agent Gamma (Option Geometry):** Runs Black-Scholes pricing to find **Zero-Debit 1x2 Ratio Spreads** ($1 \\times K_1 \\text{{ Call}} - 2 \\times K_2 \\text{{ Call}} \\approx \\$0$).
4. **Agent Delta (Swarm Overseer):** Aggregates signals and outputs the top-conviction candidate matrix.

![Swarm Chart](file:///{out_chart.replace('\\', '/')})
"""
        out_md = os.path.join(OUTPUT_DIR, "call_spread_swarm_report.md")
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(report_md)
        log_print(f"[OK] Swarm Report saved -> {out_md}")


def main():
    parser = argparse.ArgumentParser(description="Autonomous Call Spread Swarm Bot Engine")
    parser.add_argument("--once", action="store_true", help="Run scan once and exit")
    parser.add_argument("--start", action="store_true", help="Run continuous background daemon")
    args = parser.parse_args()

    overseer = SwarmOverseer()
    pid = os.getpid()

    if args.once:
        log_print(f"Starting single-pass Swarm Bot scan (PID {pid})...")
        overseer.run_swarm_scan(active_pid=pid)
        return

    log_print(f"=========================================================================")
    log_print(f"  AUTONOMOUS CALL SPREAD SWARM BOT DAEMON ACTIVE (PID: {pid})")
    log_print(f"=========================================================================")

    # Continuous daemon loop
    scan_interval = 60  # seconds between scans
    while True:
        try:
            # Check if brain state requests stop
            if os.path.exists(BRAIN_STATE_FILE):
                try:
                    with open(BRAIN_STATE_FILE, "r", encoding="utf-8") as f:
                        st = json.load(f)
                    if not st.get("is_running", True):
                        log_print("[SWARM-BOT] Stop signal received from Dashboard. Shutting down cleanly.")
                        break
                except Exception:
                    pass

            top_results = overseer.run_swarm_scan(active_pid=pid)
            top_ticker = top_results[0]["Ticker"] if top_results else "None"
            log_print(f"[SWARM-BOT] Scan complete. Top Candidate: {top_ticker}. Sleeping {scan_interval}s until next cycle...")
            time.sleep(scan_interval)
        except KeyboardInterrupt:
            log_print("[SWARM-BOT] Interrupted by user. Shutting down.")
            break
        except Exception as e:
            log_print(f"[SWARM-BOT Error] Exception in daemon loop: {e}")
            time.sleep(15)


if __name__ == "__main__":
    main()
