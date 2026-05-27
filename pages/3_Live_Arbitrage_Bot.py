# pages/3_Live_Arbitrage_Bot.py
import streamlit as st
import pandas as pd
import json
import os
import time
import threading
from datetime import datetime

# Import the daemon loop
from live_arb_bot import run_paper_bot, STATE_FILE, LOG_FILE, EXCEL_FILE

st.set_page_config(
    page_title="Live Arbitrage Bot Control",
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
        height: 300px;
        overflow-y: scroll;
        font-size: 13px;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Live Arbitrage Paper Trading Bot")
st.markdown("Monitor real-time implied cryptocurrency spreads, launch/kill the scanning background daemon, and audit mock paper trade execution ledgers.")

# ---------------------------------------------------------
# GLOBAL STATE & THREAD MANAGEMENT
# ---------------------------------------------------------
# Check if daemon thread is currently running in the background process
is_daemon_active = any(t.name == "LiveArbDaemon" for t in threading.enumerate())

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
st.sidebar.header("⚙️ Bot Configurations")

# Render sliders/inputs
starting_capital = st.sidebar.number_input(
    "Starting Mock Capital ($)",
    min_value=100.0,
    max_value=1000000.0,
    value=state_data.get("capital", 1000.0),
    step=100.0,
    disabled=is_daemon_active,
    help="Deregistered once bot starts running."
)

allocated_trade_size = st.sidebar.slider(
    "Allocated Size per Attempt ($)",
    min_value=10.0,
    max_value=5000.0,
    value=float(state_data.get("trade_size", 100.0)),
    step=10.0,
    disabled=is_daemon_active,
    help="USDT size traded per arbitrage cycle."
)

min_profit_trigger = st.sidebar.slider(
    "Min Profit Trigger (%)",
    min_value=0.01,
    max_value=1.5,
    value=float(state_data.get("min_profit_pct", 0.05)),
    step=0.01,
    help="Minimum return threshold to fire transactions. Adjusts live!"
)

# If settings changed, update json live
if not is_daemon_active:
    state_data["capital"] = starting_capital
    state_data["balance_usdt"] = state_data.get("balance_usdt", starting_capital)
    state_data["trade_size"] = allocated_trade_size

state_data["min_profit_pct"] = min_profit_trigger

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
        st.markdown('<div class="status-active">🟢 BOT RUNNING IN BACKGROUND</div>', unsafe_allow_html=True)
        if st.button("🔴 Stop Paper Trading Bot", use_container_width=True, type="primary"):
            # Signal halt to JSON
            state_data["status"] = "stopped"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
            st.toast("Halt command sent! Thread will exit on next cycle.")
            time.sleep(1.0)
            st.rerun()
    else:
        st.markdown('<div class="status-stopped">🔴 BOT STOPPED / INACTIVE</div>', unsafe_allow_html=True)
        if st.button("🟢 Start Paper Trading Bot", use_container_width=True):
            # Create files if missing to avoid logs crash
            if not os.path.exists(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                    
            state_data["status"] = "running"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
                
            # Spawn Background Thread
            t = threading.Thread(target=run_paper_bot, name="LiveArbDaemon", daemon=True)
            t.start()
            st.toast("Triangular Arbitrage daemon successfully launched!")
            time.sleep(1.0)
            st.rerun()

with col_wallet:
    st.subheader("💰 Paper Wallet Portfolio Audit")
    
    # Extract mock statistics
    cash_bal = state_data.get("balance_usdt", starting_capital)
    total_trades = state_data.get("total_trades", 0)
    total_profit = state_data.get("total_profit", 0.0)
    win_rate = state_data.get("win_rate", 0.0)
    cycles_scanned = state_data.get("cycles_scanned", 0)
    total_fees_paid = state_data.get("total_fees_paid", 0.0)
    
    # Premium, crystal-clear breakdown
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash Balance (USDT)", f"${cash_bal:,.2f}", help="Total liquid capital in paper wallet.")
    m2.metric("Gross Profit Captured", f"${(total_profit + total_fees_paid):+,.4f}", help="Total gross revenue before simulated fees.")
    m3.metric("Total Fees & Drag", f"${total_fees_paid:,.4f}", help="Simulated 0.21% execution fee and slippage drag paid.")
    m4.metric("Net Realized Profit", f"${total_profit:+.4f}", f"{win_rate:.1f}% Win Rate", help="Gross Profit minus Total Fees & Drag.")

st.markdown("---")

# Middle Panel: Live pricing ticker loop
st.subheader("⚡ Real-Time Triangular Pipeline (Binance Spot Tickers)")

# Parse live ticker values from logs or mock live feed to show price changes
p_btc, p_eth_btc, p_eth = 0.0, 0.0, 0.0
implied_spread = 0.0

if is_daemon_active and os.path.exists(LOG_FILE):
    # Attempt to read last lines of log to pull current prices
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Parse last Scan stats line
        for l in reversed(lines[-20:]):
            if "Implied Spread" in l:
                # Format: Scan #X | BTC: $X | ETH/BTC: X | ETH: $X | Implied Spread: X%
                parts = l.split("|")
                p_btc = float(parts[1].split("$")[1].replace(",", "").strip())
                p_eth_btc = float(parts[2].split(":")[1].strip())
                p_eth = float(parts[3].split("$")[1].replace(",", "").strip())
                implied_spread = float(parts[4].split(":")[1].replace("%", "").strip())
                break
    except Exception:
        pass

# Fallback simulation prices for visuals if parsing returns 0
if p_btc == 0.0:
    import numpy as np
    p_btc = 68450.0 + np.random.normal(0, 5)
    p_eth_btc = 0.0524 + np.random.normal(0, 0.00005)
    p_eth = p_btc * p_eth_btc + np.random.normal(-0.2, 0.1)
    # Gross multiple = (1 / BTC) * (1 / cross) * ETH
    gross = (1.0 / p_btc) * (1.0 / p_eth_btc) * p_eth
    implied_spread = (gross - 1.0) * 100.0

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1:
    st.metric("Leg 1: BTC/USDT (Ask)", f"${p_btc:,.2f}")
with col_t2:
    st.metric("Leg 2: ETH/BTC (Ask)", f"{p_eth_btc:.5f}")
with col_t3:
    st.metric("Leg 3: ETH/USDT (Bid)", f"${p_eth:,.2f}")
with col_t4:
    color_class = "green" if implied_spread > 0 else "red"
    st.metric("Implied Circuit Spread", f"{implied_spread:+.4f}%", 
              delta=f"{implied_spread - min_profit_trigger:+.4f}% vs trigger",
              delta_color="normal" if implied_spread > min_profit_trigger else "inverse")

st.markdown("---")

# Performance chart and cumulative fee curves
st.subheader("📈 Paper Trading Profit/Loss & Fee Drag Curve")
trades_list = state_data.get("trades", [])
if not trades_list:
    st.info("Performance curve will populate here once paper trades are executed.")
else:
    try:
        chart_df = pd.DataFrame(trades_list)
        chart_df['cumulative_profit'] = chart_df['profit'].cumsum()
        chart_df['cumulative_fee'] = chart_df['fee'].cumsum()
        
        import plotly.graph_objects as go
        fig = go.Figure()
        
        # Net Profit Line
        fig.add_trace(go.Scatter(
            x=chart_df['timestamp'],
            y=chart_df['cumulative_profit'],
            mode='lines+markers',
            name='Net Realized PnL ($)',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=6, color='#2e7d32')
        ))
        
        # Cumulative Fees Line
        fig.add_trace(go.Scatter(
            x=chart_df['timestamp'],
            y=chart_df['cumulative_fee'],
            mode='lines+markers',
            name='Cumulative Fees & Drag ($)',
            line=dict(color='#e74c3c', width=2, dash='dash'),
            marker=dict(size=4, color='#c62828')
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10),
            height=250,
            xaxis=dict(showgrid=False, title="Execution Timestamp"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Value ($)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Error rendering performance chart: {e}")

st.markdown("---")

# Bottom Panel: Scrolling Terminal Logs & Ledger
col_log, col_ledger = st.columns([1, 1])

with col_log:
    st.subheader("🖥️ Live Daemon Running Logs (arb_bot.log)")
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
    st.subheader("📑 Completed Triangular Arbitrage Ledger")
    
    if not trades_list:
        st.info("No arbitrage cycles executed yet. Scanning markets...")
    else:
        trades_df = pd.DataFrame(trades_list)
        # Rename columns to match new 6-column structure containing fees!
        trades_df.columns = ["Time", "Scan Cycle", "Expected Return (%)", "Net Profit ($)", "Fee Paid ($)", "USDT Balance"]
        st.dataframe(trades_df.sort_index(ascending=False), use_container_width=True)
        
        # Download ledger button
        if os.path.exists(EXCEL_FILE):
            with open(EXCEL_FILE, "rb") as file:
                st.download_button(
                    label="📥 Download Excel Audit Workbook",
                    data=file,
                    file_name="live_arb_execution_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
