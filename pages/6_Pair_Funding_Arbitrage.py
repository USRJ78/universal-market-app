# pages/6_Pair_Funding_Arbitrage.py
import streamlit as st
import pandas as pd
import json
import os
import time
import threading
from datetime import datetime

# Import daemon loop configs
from pair_funding_arb_bot import run_pair_funding_bot, STATE_FILE, LOG_FILE, EXCEL_FILE, DEFAULT_PAIRS

st.set_page_config(
    page_title="Tactical Pair Funding Arbitrage",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    .status-active {
        background-color: rgba(46, 204, 113, 0.15);
        border: 1px solid rgb(46, 204, 113);
        border-radius: 8px;
        padding: 12px 20px;
        color: #2ecc71;
        font-weight: 700;
        text-align: center;
        margin-bottom: 15px;
    }
    .status-stopped {
        background-color: rgba(231, 76, 60, 0.15);
        border: 1px solid rgb(231, 76, 60);
        border-radius: 8px;
        padding: 12px 20px;
        color: #e74c3c;
        font-weight: 700;
        text-align: center;
        margin-bottom: 15px;
    }
    .terminal-box {
        background-color: #0f172a;
        color: #38bdf8;
        font-family: 'Courier New', Courier, monospace;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        height: 250px;
        overflow-y: scroll;
        font-size: 13px;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

st.title("💫 Tactical Double-Sided Pair Funding Arbitrage")
st.markdown("Harvest high-yield perp funding payments on **BOTH legs simultaneously** by holding equal and opposite correlated positions (e.g. Long BCH + Short LTC) entered tactically minutes before settlement boundary.")

# ---------------------------------------------------------
# GLOBAL STATE & THREAD MANAGEMENT
# ---------------------------------------------------------
# Check if daemon thread is currently running in the background process
is_daemon_active = any(t.name == "PairFundingDaemon" for t in threading.enumerate())

# Force check state file
state_data = {}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state_data = json.load(f)
    except Exception:
        pass

# Align state file status with actual daemon running status
status_str = "stopped"
if is_daemon_active:
    status_str = "running"
    
if state_data.get("status") != status_str:
    state_data["status"] = status_str
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
    except Exception:
        pass

# Sidebar Configurations
st.sidebar.header("⚙️ Arbitrage Configurations")

# Display credentials status
api_key = state_data.get("api_key", "")
api_secret = state_data.get("api_secret", "")

if api_key and api_secret and "paste_your" not in api_key:
    st.sidebar.markdown(
        '<div style="background-color: rgba(46, 204, 113, 0.15); border: 1px solid #2ecc71; border-radius: 6px; padding: 10px; margin-bottom: 15px; font-size: 13px; color: #2ecc71; text-align: center; font-weight: 600;">'
        '🔑 Streamlit Secrets Loaded'
        '</div>',
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        '<div style="background-color: rgba(243, 156, 18, 0.15); border: 1px solid #f39c12; border-radius: 6px; padding: 10px; margin-bottom: 15px; font-size: 13px; color: #f39c12; text-align: center; font-weight: 600;">'
        '⚠️ Paper Sandbox Mode Only<br><span style="font-weight: normal; font-size: 11px;">(Secrets file missing or empty)</span>'
        '</div>',
        unsafe_allow_html=True
    )

execution_mode = st.sidebar.selectbox(
    "Execution Mode",
    ["Paper Sandbox (Mock)", "Live Account (Real)"],
    index=0 if state_data.get("execution_mode", "paper") == "paper" else 1,
    disabled=is_daemon_active,
    help="Switch between simulated mock runs and actual real market trading on your Binance account."
)
mode_val = "paper" if execution_mode == "Paper Sandbox (Mock)" else "live"

position_allocation = st.sidebar.slider(
    "Margin Size per Pair ($)",
    min_value=50.0,
    max_value=2000.0,
    value=float(state_data.get("position_allocation", 250.0)),
    step=50.0,
    disabled=is_daemon_active,
    help="USDT cash margin budget locked up per active pair. Symmetrically allocated 50% Long, 50% Short."
)

futures_leverage = st.sidebar.slider(
    "Pair Futures Leverage",
    min_value=1.0,
    max_value=10.0,
    value=float(state_data.get("futures_leverage", 5.0)),
    step=1.0,
    disabled=is_daemon_active,
    help="Leverage applied symmetrically on both derivative contract legs. Freeing up capital margin."
)

min_apr_trigger = st.sidebar.slider(
    "Min Combined APR Spread (%)",
    min_value=2.0,
    max_value=30.0,
    value=float(state_data.get("min_apr_trigger", 10.0)),
    step=0.5,
    help="Minimum combined annualized yield spread (Short APR - Long APR) required to open pair positions."
)

# Save configurations live if not running
if not is_daemon_active:
    state_data["position_allocation"] = position_allocation
    state_data["futures_leverage"] = futures_leverage
    state_data["min_apr_trigger"] = min_apr_trigger
    state_data["execution_mode"] = mode_val

try:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=4)
except Exception:
    pass

# Main Dashboard Layout
col_ctrl, col_wallet = st.columns([1, 2])

with col_ctrl:
    st.subheader("🕹️ Daemon Controller")
    if is_daemon_active:
        st.markdown('<div class="status-active">🟢 TACTICAL DAEMON ACTIVE</div>', unsafe_allow_html=True)
        if st.button("🔴 Stop Arbitrage Bot", use_container_width=True, type="primary"):
            state_data["status"] = "stopped"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
            st.toast("Halt command sent! Thread will exit on next cycle.")
            time.sleep(1.0)
            st.rerun()
    else:
        st.markdown('<div class="status-stopped">🔴 DEACTIVATED / INACTIVE</div>', unsafe_allow_html=True)
        if st.button("🟢 Start Arbitrage Bot", use_container_width=True):
            if not os.path.exists(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
            
            # Start fresh and clear active metric caches
            state_data["status"] = "running"
            state_data["total_trades"] = 0
            state_data["cycles_scanned"] = 0
            state_data["positions"] = []
            state_data["trades"] = []
            state_data["total_fees_paid"] = 0.0
            
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
                
            # Spawn Background Thread
            t = threading.Thread(target=run_pair_funding_bot, name="PairFundingDaemon", daemon=True)
            t.start()
            st.toast("Tactical Pair Funding Arbitrage daemon successfully launched!")
            time.sleep(1.0)
            st.rerun()

with col_wallet:
    st.subheader("💰 Paper Wallet Portfolio Audit")
    
    # Extract mock statistics
    cash_bal = state_data.get("balance_usdt", 1000.0)
    total_trades = state_data.get("total_trades", 0)
    total_fees_paid = state_data.get("total_fees_paid", 0.0)
    positions_list = state_data.get("positions", [])
    active_positions_count = len(positions_list)
    invested_margin = active_positions_count * position_allocation
    total_equity = cash_bal + invested_margin
    
    # Premium glassmorphic metric cards
    st.markdown(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; width: 100%;">
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Net Equity</div>
            <div style="font-size: 18px; font-weight: 700; color: #38bdf8; margin-top: 6px;">${total_equity:,.4f}</div>
            <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Liquidation Value</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Liquid Cash</div>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 6px;">${cash_bal:,.2f}</div>
            <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Available USDT</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Invested Capital</div>
            <div style="font-size: 18px; font-weight: 700; color: #e2e8f0; margin-top: 6px;">${invested_margin:,.2f}</div>
            <div style="font-size: 10px; color: #38bdf8; margin-top: 4px; font-weight: 600;">{active_positions_count} Active Pairs</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Total Trades</div>
            <div style="font-size: 18px; font-weight: 700; color: #c084fc; margin-top: 6px;">{total_trades}</div>
            <div style="font-size: 10px; color: #f87171; margin-top: 4px; font-weight: 600;">${total_fees_paid:.4f} Fees</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Middle Panel: Opportunity Grid & Active Positions
col_grid, col_positions = st.columns([1, 1])

# Load pair log if available
pair_arbitrage_list = []
log_file_path = "pair_funding_arbitrage_log.json"
if os.path.exists(log_file_path):
    try:
        with open(log_file_path, "r", encoding="utf-8") as lf:
            log_data = json.load(lf)
            pair_arbitrage_list = log_data.get("arbitrage_pairs", [])
    except Exception:
        pass

with col_grid:
    st.subheader("⚡ Live Double-Sided Pair Funding Grid")
    
    if not pair_arbitrage_list:
        # Default display while daemon fetches data
        grid_rows = []
        for pair in DEFAULT_PAIRS:
            grid_rows.append({
                "Arbitrage Pair": pair["name"],
                "Long Leg": f"{pair['long']} (-0.0150%)",
                "Short Leg": f"{pair['short']} (+0.0080%)",
                "Combined Spread": "0.0230%",
                "Combined APR (%)": "25.18%",
                "Double-Yield?": "🟢 YES",
                "Countdown": "N/A"
            })
        st.dataframe(pd.DataFrame(grid_rows).set_index("Arbitrage Pair"), use_container_width=True)
    else:
        grid_rows = []
        for p in pair_arbitrage_list:
            grid_rows.append({
                "Arbitrage Pair": p["pair_name"],
                "Long Leg": f"{p['long_asset']} ({p['long_rate']:+.4%})",
                "Short Leg": f"{p['short_asset']} ({p['short_rate']:+.4%})",
                "Combined Spread": f"{p['net_rate']:+.4%}",
                "Combined APR (%)": f"{p['combined_apr']:.2f}%",
                "Double-Yield?": "🟢 YES" if p["is_double_yield"] else "🔴 NO",
                "Countdown": p["countdown"]
            })
        st.dataframe(pd.DataFrame(grid_rows).set_index("Arbitrage Pair"), use_container_width=True)

with col_positions:
    st.subheader("💼 Active Hedged Pairs Desk")
    
    if not positions_list:
        st.info("No active pair positions held. The bot will automatically trigger opens exactly 5 minutes before interval crossover.")
    else:
        pos_rows = []
        for pos in positions_list:
            pos_rows.append({
                "Pair Strategy": pos["pair_name"],
                "Long Asset": pos["long_asset"],
                "Short Asset": pos["short_asset"],
                "Hedged Size ($)": f"${pos['position_size']:.2f}",
                "Futures Margin": f"${pos['margin_allocated']:.2f} ({pos['leverage']:.0f}x)",
                "Combined APR": f"{(pos['short_apr'] - pos['long_apr']):.2f}%",
                "Funding Captured": f"${pos['funding_received']:.4f}",
                "Settled?": "✅ YES" if pos["settled"] else "⏳ COUNTDOWN"
            })
        st.dataframe(pd.DataFrame(pos_rows).set_index("Pair Strategy"), use_container_width=True)
        st.caption("Active pair arbitrage. Leg 1 (Long) and Leg 2 (Short) physically hedge each other, neutralizing the portfolio against direction risk while extracting dual-leg funding payout.")

st.markdown("---")

# Bottom Panel: Scrolling Terminal Logs & Ledger
col_log, col_ledger = st.columns([1, 1])

with col_log:
    st.subheader("🖥️ Live Pair Yield Daemon Running Logs")
    log_text = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            log_text = "".join(log_lines[-25:])
        except Exception as e:
            log_text = f"Error reading logs: {e}"
    else:
        log_text = "Bot inactive. Terminal logs will appear here once started."
        
    st.markdown(f'<div class="terminal-box">{log_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
    
    # Auto-refresh checkbox
    autorefresh = st.checkbox("Enable Real-time Auto-Refresh (3s)", value=is_daemon_active)
    if autorefresh:
        time.sleep(3.0)
        st.rerun()

with col_ledger:
    st.subheader("📑 Completed Pair Arbitrage Ledger")
    trades_list = state_data.get("trades", [])
    
    if not trades_list:
        st.info("No tactical pair arbitrage cycles completed yet.")
    else:
        trades_df = pd.DataFrame(trades_list)
        trades_df.columns = ["Time", "Pair Strategy", "Action", "Allocated Margin ($)", "Combined APR (%)", "Net Profit ($)", "Fee Paid ($)"]
        st.dataframe(trades_df.sort_index(ascending=False), use_container_width=True)
        
        # Download Excel audit workbook button
        if os.path.exists(EXCEL_FILE):
            with open(EXCEL_FILE, "rb") as file:
                st.download_button(
                    label="📥 Download Excel Audit Workbook",
                    data=file,
                    file_name="pair_funding_arb_execution_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
