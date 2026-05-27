# pages/4_Funding_Arbitrage.py
import streamlit as st
import pandas as pd
import json
import os
import time
import threading
from datetime import datetime

# Import daemon loop configs
from funding_arb_bot import run_funding_bot, STATE_FILE, LOG_FILE, EXCEL_FILE

st.set_page_config(
    page_title="Live Funding Arbitrage Control",
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

st.title("🛡️ Live Funding Rate Arbitrage Control Panel")
st.markdown("Harvest high-yield perp funding payments with **zero asset direction risk** by holding equal Spot (Long) and Perpetual Futures (Short) positions.")

# ---------------------------------------------------------
# GLOBAL STATE & THREAD MANAGEMENT
# ---------------------------------------------------------
# Check if daemon thread is currently running in the background process
is_daemon_active = any(t.name == "LiveFundingDaemon" for t in threading.enumerate())

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

starting_capital = st.sidebar.number_input(
    "Starting Mock Capital ($)",
    min_value=100.0,
    max_value=1000000.0,
    value=state_data.get("capital", 1000.0),
    step=100.0,
    disabled=is_daemon_active,
    help="Capital for simulated paper trading."
)

position_allocation = st.sidebar.slider(
    "Size per Position ($)",
    min_value=50.0,
    max_value=2000.0,
    value=float(state_data.get("position_allocation", 250.0)),
    step=50.0,
    disabled=is_daemon_active,
    help="Cash allocated per active asset (divided into equal spot and perp short)."
)

min_apr_trigger = st.sidebar.slider(
    "Entry APR Trigger (%)",
    min_value=1.0,
    max_value=30.0,
    value=float(state_data.get("min_apr_trigger", 8.0)),
    step=0.5,
    help="Minimum annualized yield (APR) required to open delta-neutral positions."
)

stop_apr_trigger = st.sidebar.slider(
    "Exit APR Trigger (%)",
    min_value=0.0,
    max_value=15.0,
    value=float(state_data.get("stop_apr_trigger", 2.0)),
    step=0.5,
    help="APR threshold below which active positions are unwound cleanly."
)

# Save configurations live if not running
if not is_daemon_active:
    state_data["capital"] = starting_capital
    state_data["balance_usdt"] = state_data.get("balance_usdt", starting_capital)
    state_data["position_allocation"] = position_allocation

state_data["min_apr_trigger"] = min_apr_trigger
state_data["stop_apr_trigger"] = stop_apr_trigger

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
        st.markdown('<div class="status-active">🟢 YIELD DAEMON ACTIVE</div>', unsafe_allow_html=True)
        if st.button("🔴 Stop Arbitrage Bot", use_container_width=True, type="primary"):
            # Signal halt to JSON
            state_data["status"] = "stopped"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
            st.toast("Halt command sent! Thread will exit on next cycle.")
            time.sleep(1.0)
            st.rerun()
    else:
        st.markdown('<div class="status-stopped">🔴 DEACTIVATED / INACTIVE</div>', unsafe_allow_html=True)
        if st.button("🟢 Start Arbitrage Bot", use_container_width=True):
            # Create files if missing
            if not os.path.exists(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                    
            state_data["status"] = "running"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
                
            # Spawn Background Thread
            t = threading.Thread(target=run_funding_bot, name="LiveFundingDaemon", daemon=True)
            t.start()
            st.toast("Delta-Neutral Funding Arbitrage daemon successfully launched!")
            time.sleep(1.0)
            st.rerun()

with col_wallet:
    st.subheader("💰 Paper Wallet Portfolio Audit")
    
    # Extract mock statistics
    cash_bal = state_data.get("balance_usdt", starting_capital)
    total_trades = state_data.get("total_trades", 0)
    total_yield = state_data.get("total_yield", 0.0)
    active_positions_count = len(state_data.get("positions", []))
    
    # Calculate average active APR
    positions_list = state_data.get("positions", [])
    avg_apr = sum(p["apr"] for p in positions_list) / len(positions_list) if positions_list else 0.0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash Balance (USDT)", f"${cash_bal:,.2f}")
    m2.metric("Positions Held", f"{active_positions_count}")
    m3.metric("Accrued Yield Captured", f"${total_yield:.6f}")
    m4.metric("Avg Portfolio APR", f"{avg_apr:.2f}%", f"{total_trades} Completed Trades")

st.markdown("---")

# Middle Panel: Opportunity Grid & Active Positions
col_grid, col_positions = st.columns([1, 1])

with col_grid:
    st.subheader("⚡ Live Funding Rate Yield Grid")
    
    # Pull current rates from logs
    rates_rows = []
    assets = ["BTC", "ETH", "SOL", "ADA", "XRP"]
    
    p_spots = {"BTC": 68250.0, "ETH": 3820.0, "SOL": 166.2, "ADA": 0.485, "XRP": 0.522}
    p_perps = {"BTC": 68265.0, "ETH": 3821.5, "SOL": 166.4, "ADA": 0.486, "XRP": 0.523}
    p_aprs = {"BTC": 11.2, "ETH": 9.5, "SOL": 14.8, "ADA": 5.4, "XRP": 4.1}
    
    if is_daemon_active and os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Parse scan status lines
            for l in reversed(lines[-25:]):
                # Format: · BTC  | Spot: $X | Perp: $X | Funding APR: X%
                if "·" in l and "|" in l:
                    parts = l.split("|")
                    asset = parts[0].replace("·", "").strip()
                    spot = float(parts[1].split("$")[1].replace(",", "").strip())
                    perp = float(parts[2].split("$")[1].replace(",", "").strip())
                    apr = float(parts[3].split(":")[1].replace("%", "").strip())
                    
                    p_spots[asset] = spot
                    p_perps[asset] = perp
                    p_aprs[asset] = apr
        except Exception:
            pass
            
    for asset in assets:
        rates_rows.append({
            "Asset": asset,
            "Spot Price": f"${p_spots[asset]:,.2f}",
            "Perp Price": f"${p_perps[asset]:,.2f}",
            "Perp Basis Spread": f"${(p_perps[asset] - p_spots[asset]):+,.2f}",
            "Annualized APR (%)": f"{p_aprs[asset]:.2f}%"
        })
    grid_df = pd.DataFrame(rates_rows)
    st.dataframe(grid_df.set_index("Asset"), use_container_width=True)

with col_positions:
    st.subheader("💼 Active Delta-Neutral Positions Desk")
    
    if not positions_list:
        st.info("No active delta-neutral positions currently held. Waiting for APR triggers...")
    else:
        pos_rows = []
        for pos in positions_list:
            pos_rows.append({
                "Asset": pos["asset"],
                "Spot Entry": f"${pos['spot_price']:,.2f}",
                "Perp Entry": f"${pos['perp_price']:,.2f}",
                "Position Size ($)": f"${pos['size']:,.2f}",
                "Active APR (%)": f"{pos['apr']:.2f}%",
                "Accrued Yield ($)": f"${pos['yield_captured']:.6f}"
            })
        pos_df = pd.DataFrame(pos_rows)
        st.dataframe(pos_df.set_index("Asset"), use_container_width=True)
        st.caption("Positions held are perfectly hedge-neutral. Long Spot position offsets Short Perpetual position.")

st.markdown("---")

# Bottom Panel: Scrolling Terminal Logs & Ledger
col_log, col_ledger = st.columns([1, 1])

with col_log:
    st.subheader("🖥️ Live Yield Daemon Running Logs (funding_arb.log)")
    log_text = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            log_text = "".join(log_lines[-25:]) # display last 25 lines
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
    st.subheader("📑 Completed Yield Arbitrage Ledger")
    
    trades_list = state_data.get("trades", [])
    if not trades_list:
        st.info("No yield arbitrage cycles completed yet.")
    else:
        trades_df = pd.DataFrame(trades_list)
        trades_df.columns = ["Time", "Asset", "Action", "Allocated Size ($)", "Captured APR (%)", "Net Profit ($)"]
        st.dataframe(trades_df.sort_index(ascending=False), use_container_width=True)
        
        # Download Excel audit button
        if os.path.exists(EXCEL_FILE):
            with open(EXCEL_FILE, "rb") as file:
                st.download_button(
                    label="📥 Download Excel Audit Workbook",
                    data=file,
                    file_name="funding_arb_execution_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
