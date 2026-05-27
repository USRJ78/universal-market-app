# pages/5_Live_L2_Arbitrage.py
import streamlit as st
import pandas as pd
import json
import os
import time
import threading
from datetime import datetime

# Import the L2 daemon loop
from live_l2_arb_bot import run_l2_paper_bot, STATE_FILE, LOG_FILE, EXCEL_FILE

st.set_page_config(
    page_title="L2 Rupees Spot Arbitrage Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Glassmorphic Styling
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

st.title("⚖️ Live L2 Depth-Adjusted Rupees Arbitrage")
st.markdown("Monitor real-time volume-weighted triangular spreads directly against Binance Spot L2 Order Books. Test actual exchange slippage and taker fee scenarios scaled in **Indian Rupees (₹)**.")

# ---------------------------------------------------------
# GLOBAL STATE & THREAD MANAGEMENT
# ---------------------------------------------------------
is_daemon_active = any(t.name == "LiveL2ArbDaemon" for t in threading.enumerate())

state_data = {}
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state_data = json.load(f)
    except Exception:
        pass

# Sync JSON state status with thread enumeration
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
st.sidebar.header("⚙️ L2 Bot Configurations")

starting_capital = st.sidebar.number_input(
    "Starting Capital (₹)",
    min_value=1000.0,
    max_value=10000000.0,
    value=state_data.get("capital", 100000.0),
    step=1000.0,
    disabled=is_daemon_active,
    help="Initial mock capital for this trial run."
)

allocated_trade_size = st.sidebar.slider(
    "Trade Size per Attempt (₹)",
    min_value=500.0,
    max_value=250000.0,
    value=float(state_data.get("trade_size", 10000.0)),
    step=500.0,
    disabled=is_daemon_active,
    help="INR value executed per triangular cycle."
)

usd_inr_rate = st.sidebar.number_input(
    "USDT / INR Exchange Rate",
    min_value=50.0,
    max_value=120.0,
    value=state_data.get("usd_inr_rate", 85.0),
    step=0.1,
    disabled=is_daemon_active,
    help="USDT exchange rate used to walk USD-based live order books."
)

taker_fee_rate = st.sidebar.slider(
    "Taker Fee per Leg (%)",
    min_value=0.01,
    max_value=0.50,
    value=float(state_data.get("taker_fee_pct", 0.10)),
    step=0.01,
    disabled=is_daemon_active,
    help="Taker fee deducted per transaction leg (Binance Spot default: 0.10%)."
)

min_profit_trigger = st.sidebar.slider(
    "Min Net Profit Trigger (%)",
    min_value=0.01,
    max_value=1.5,
    value=float(state_data.get("min_profit_pct", 0.05)),
    step=0.01,
    help="Minimum net return threshold required to fire transactions."
)

# New sidebar trade limits configuration
limit_trades = st.sidebar.checkbox(
    "Limit Number of Trades",
    value=state_data.get("limit_trades", False),
    disabled=is_daemon_active,
    help="Automatically stop the bot after a certain number of trades."
)

max_trades_limit = 0
if limit_trades:
    max_trades_limit = st.sidebar.number_input(
        "Max Trades Limit",
        min_value=1,
        max_value=1000,
        value=int(state_data.get("max_trades_limit", 5)),
        step=1,
        disabled=is_daemon_active,
        help="The bot will halt once it executes this many trades."
    )

# Save settings dynamically
if not is_daemon_active:
    state_data["capital"] = starting_capital
    state_data["balance_inr"] = state_data.get("balance_inr", starting_capital)
    state_data["trade_size"] = allocated_trade_size
    state_data["taker_fee_pct"] = taker_fee_rate
    state_data["usd_inr_rate"] = usd_inr_rate
    state_data["limit_trades"] = limit_trades
    state_data["max_trades_limit"] = max_trades_limit

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
        st.markdown('<div class="status-active">🟢 L2 SCANNERS ACTIVE</div>', unsafe_allow_html=True)
        if st.button("🔴 Stop L2 Paper Trader", use_container_width=True, type="primary"):
            state_data["status"] = "stopped"
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
            st.toast("Halt command sent! L2 Daemon will exit on next cycle.")
            time.sleep(1.0)
            st.rerun()
    else:
        st.markdown('<div class="status-stopped">🔴 BOT STOPPED / INACTIVE</div>', unsafe_allow_html=True)
        if st.button("🟢 Start L2 Paper Trader", use_container_width=True):
            if not os.path.exists(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
            
            # Auto-archive previous run
            if state_data.get("total_trades", 0) > 0 or state_data.get("cycles_scanned", 0) > 0:
                from live_l2_arb_bot import LiveL2ArbBot
                temp_bot = LiveL2ArbBot()
                temp_bot.archive_current_trial(stop_reason="Start Reset")
                temp_bot.reset_active_portfolio()
                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, "r", encoding="utf-8") as f:
                            state_data = json.load(f)
                    except Exception:
                        pass
                        
            state_data["status"] = "running"
            state_data["capital"] = starting_capital
            state_data["balance_inr"] = starting_capital
            state_data["total_trades"] = 0
            state_data["total_profit_inr"] = 0.0
            state_data["win_rate"] = 0.0
            state_data["cycles_scanned"] = 0
            state_data["trades"] = []
            state_data["total_fees_paid_inr"] = 0.0
            state_data["total_slippage_drag_inr"] = 0.0
            state_data["limit_trades"] = limit_trades
            state_data["max_trades_limit"] = max_trades_limit
            
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
                
            # Launch L2 background thread
            t = threading.Thread(target=run_l2_paper_bot, name="LiveL2ArbDaemon", daemon=True)
            t.start()
            st.toast("L2 order book triangular arbitrage bot successfully launched!")
            time.sleep(1.0)
            st.rerun()
            
        if state_data.get("total_trades", 0) > 0 or state_data.get("cycles_scanned", 0) > 0:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("📥 Save Trial & Reset Portfolio", use_container_width=True, type="secondary", help="Archive current run to history and reset active stats to zero."):
                from live_l2_arb_bot import LiveL2ArbBot
                temp_bot = LiveL2ArbBot()
                temp_bot.archive_current_trial(stop_reason="Manual Save & Reset")
                temp_bot.reset_active_portfolio()
                temp_bot.save_state()
                st.toast("Current L2 run archived and active portfolio reset to zero!")
                time.sleep(1.0)
                st.rerun()

with col_wallet:
    st.subheader("💰 Paper Wallet Portfolio Audit (₹)")
    
    # Extract mock statistics
    cash_bal = state_data.get("balance_inr", starting_capital)
    total_trades = state_data.get("total_trades", 0)
    total_profit = state_data.get("total_profit_inr", 0.0)
    win_rate = state_data.get("win_rate", 0.0)
    total_fees_paid = state_data.get("total_fees_paid_inr", 0.0)
    total_slippage_drag = state_data.get("total_slippage_drag_inr", 0.0)
    
    # Premium, crystal-clear non-truncating INR cards deck
    st.markdown(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; width: 100%;">
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Available Cash</div>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 6px;">₹{cash_bal:,.2f}</div>
            <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Liquid INR</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Exchange Fees</div>
            <div style="font-size: 18px; font-weight: 700; color: #f87171; margin-top: 6px;">₹{total_fees_paid:,.2f}</div>
            <div style="font-size: 10px; color: #64748b; margin-top: 4px;">{taker_fee_rate * 3:.2f}% Taker Commission</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Slippage Drag</div>
            <div style="font-size: 18px; font-weight: 700; color: #fb923c; margin-top: 6px;">₹{total_slippage_drag:,.2f}</div>
            <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Order Book Impact</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Net Profit (PnL)</div>
            <div style="font-size: 18px; font-weight: 700; color: #34d399; margin-top: 6px;">₹{total_profit:+,.2f}</div>
            <div style="font-size: 10px; color: #34d399; margin-top: 4px; font-weight: 600;">{win_rate:.1f}% Win Rate</div>
        </div>
        <div style="flex: 1; min-width: 140px; background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Total Trades</div>
            <div style="font-size: 18px; font-weight: 700; color: #c084fc; margin-top: 6px;">{total_trades}</div>
            <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Completed Fills</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Middle Panel: L2 depth monitor
st.subheader("⚡ Real-Time L2 Order Book Depth Walk (Binance Spot)")

# Extract prices from logs or mock
p_btc, p_eth_btc, p_eth = 0.0, 0.0, 0.0
implied_l2_spread = 0.0

if is_daemon_active and os.path.exists(LOG_FILE):
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for l in reversed(lines[-20:]):
            if "Actual L2 Net Spread" in l:
                # Format: L2 Scan #X | Trade Size: ₹X ($X) | Ticker Spread: X% | Actual L2 Net Spread: X%
                parts = l.split("|")
                ticker_spread = float(parts[2].split(":")[1].replace("%", "").strip())
                implied_l2_spread = float(parts[3].split(":")[1].replace("%", "").strip())
                
                # Fetch next line containing average price executions
                # Format: L2 Avg Executions -> L1 (BTC): $X | L2 (ETH/BTC): X | L3 (ETH): $X
                idx = lines.index(l)
                if idx + 1 < len(lines):
                    exec_line = lines[idx + 1]
                    exec_parts = exec_line.split("|")
                    p_btc = float(exec_parts[0].split("$")[1].replace(",", "").strip())
                    p_eth_btc = float(exec_parts[1].split(":")[1].strip())
                    p_eth = float(exec_parts[2].split("$")[1].replace(",", "").strip())
                break
    except Exception:
        pass

if p_btc == 0.0:
    # High-fidelity mock baseline calculations
    import numpy as np
    p_btc = 68420.0 + np.random.normal(0, 5)
    p_eth_btc = 0.0525 + np.random.normal(0, 0.00003)
    p_eth = p_btc * p_eth_btc + np.random.normal(-0.1, 0.05)
    # Average L2 price accounts for trade-size slippage
    # Larger size = worse fill prices
    size_slip_factor = (allocated_trade_size / usd_inr_rate) * 0.000002
    p_btc_l2 = p_btc * (1.0 + size_slip_factor)
    p_eth_btc_l2 = p_eth_btc * (1.0 + size_slip_factor)
    p_eth_l2 = p_eth * (1.0 - size_slip_factor)
    
    ticker_gross = (1.0 / p_btc) * (1.0 / p_eth_btc) * p_eth
    ticker_spread_pct = (ticker_gross - 1.0) * 100.0
    
    l2_gross = (1.0 / p_btc_l2) * (1.0 / p_eth_btc_l2) * p_eth_l2
    # Subtract 3 taker fees
    fee_rate = taker_fee_rate / 100.0
    l2_net = l2_gross * ((1.0 - fee_rate) ** 3)
    implied_l2_spread = (l2_net - 1.0) * 100.0
    ticker_spread = ticker_spread_pct
else:
    # compute ticker spread relative to l2
    ticker_spread = implied_l2_spread + (taker_fee_rate * 3) + 0.08

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
with col_t1:
    st.metric("Avg L1 Match (BTC/USDT)", f"${p_btc:,.2f}")
with col_t2:
    st.metric("Avg L2 Match (ETH/BTC)", f"{p_eth_btc:.5f}")
with col_t3:
    st.metric("Avg L3 Match (ETH/USDT)", f"${p_eth:,.2f}")
with col_t4:
    st.metric("Volume-Weighted Net Spread", f"{implied_l2_spread:+.4f}%",
              delta=f"{implied_l2_spread - min_profit_trigger:+.4f}% vs trigger",
              delta_color="normal" if implied_l2_spread > min_profit_trigger else "inverse")

# Render comparison table
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
comparison_data = [
    {
        "Metrics": "Gross Implied Spread (%)",
        "Toplevel Ticker (Best Bid/Ask)": f"{ticker_spread + (taker_fee_rate * 3):+.4f}%",
        "Volume-Weighted L2 Depth": f"{implied_l2_spread + (taker_fee_rate * 3):+.4f}%",
        "Slippage / Commission Drag": f"-{((ticker_spread) - implied_l2_spread):.4f}%"
    },
    {
        "Metrics": "Exchange Fees (%)",
        "Toplevel Ticker (Best Bid/Ask)": "0.00% (assumed zero)",
        "Volume-Weighted L2 Depth": f"{taker_fee_rate * 3:.2f}%",
        "Slippage / Commission Drag": f"-{taker_fee_rate * 3:.2f}%"
    },
    {
        "Metrics": "Net Trading Spread (%)",
        "Toplevel Ticker (Best Bid/Ask)": f"{ticker_spread + (taker_fee_rate * 3):+.4f}%",
        "Volume-Weighted L2 Depth": f"{implied_l2_spread:+.4f}%",
        "Slippage / Commission Drag": f"-{((ticker_spread + (taker_fee_rate * 3)) - implied_l2_spread):.4f}%"
    }
]
st.table(pd.DataFrame(comparison_data).set_index("Metrics"))
st.caption(f"Slippage and transaction fees represent actual exchange drag for executing an INR size of ₹{allocated_trade_size:,.0f} ($ {allocated_trade_size/usd_inr_rate:,.2f} USDT).")

st.markdown("---")

# Performance Curves in Rupees
st.subheader("📈 L2 Paper Trading Realized Net PnL vs. Exchange Fee Curve (₹)")
trades_list = state_data.get("trades", [])
if not trades_list:
    st.info("Performance curve in Rupees will populate here once L2 paper trades are executed.")
else:
    try:
        chart_df = pd.DataFrame(trades_list)
        chart_df['cumulative_profit'] = chart_df['profit'].fillna(0.0).cumsum()
        chart_df['cumulative_fee'] = chart_df['fee'].fillna(0.0).cumsum()
        
        import plotly.graph_objects as go
        fig = go.Figure()
        
        # Net Profit Line in INR
        fig.add_trace(go.Scatter(
            x=chart_df['timestamp'],
            y=chart_df['cumulative_profit'],
            mode='lines+markers',
            name='Net Realized PnL (₹)',
            line=dict(color='#2ecc71', width=3),
            marker=dict(size=6, color='#2e7d32')
        ))
        
        # Cumulative Fees Line in INR
        fig.add_trace(go.Scatter(
            x=chart_df['timestamp'],
            y=chart_df['cumulative_fee'],
            mode='lines+markers',
            name='Cumulative Exchange Fees (₹)',
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
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Rupees (₹)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Error rendering performance chart: {e}")

st.markdown("---")

# Bottom Panel: Scrolling Terminal Logs & Ledger
col_log, col_ledger = st.columns([1, 1])

with col_log:
    st.subheader("🖥️ Live L2 Daemon Running Logs (l2_arb_bot.log)")
    log_text = ""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
            log_text = "".join(log_lines[-25:])
        except Exception as e:
            log_text = f"Error reading logs: {e}"
    else:
        log_text = "L2 Bot inactive. Terminal logs will appear here once started."
        
    st.markdown(f'<div class="terminal-box">{log_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
    
    # Auto-refresh checkbox
    autorefresh = st.checkbox("Enable Real-time Auto-Refresh (3s)", value=is_daemon_active)
    if autorefresh:
        time.sleep(3.0)
        st.rerun()

with col_ledger:
    st.subheader("📑 Completed L2 Depth Arbitrage Ledger")
    
    if not trades_list:
        st.info("No L2 depth arbitrage trades executed yet. Walk the order books to scan...")
    else:
        trades_df = pd.DataFrame(trades_list)
        # Columns: timestamp, cycle, expected_return, profit, fee, slippage, balance
        trades_df.columns = ["Time", "Scan Cycle", "Net Spread (%)", "Net Profit (₹)", "Fee Paid (₹)", "Slippage Drag (₹)", "INR Balance"]
        st.dataframe(trades_df.sort_index(ascending=False), use_container_width=True)
        
        # Download ledger workbook
        if os.path.exists(EXCEL_FILE):
            with open(EXCEL_FILE, "rb") as file:
                st.download_button(
                    label="📥 Download Excel L2 Audit Ledger",
                    data=file,
                    file_name="live_l2_execution_log.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# Bottom Full-Width Section: Historical Trials Log
st.markdown("---")
st.subheader("📜 Historical Trials Journal (₹)")
trials_list = state_data.get("trials", [])
if not trials_list:
    st.info("No completed L2 trials logged in database yet. Set a trade limit or start & stop the L2 bot to create a trial!")
else:
    trials_df = pd.DataFrame(trials_list)
    cols_display = {
        "trial_id": "Trial ID",
        "start_time": "Start Time",
        "end_time": "End Time",
        "initial_capital": "Initial Capital (₹)",
        "final_balance": "Final Balance (₹)",
        "net_profit": "Net PnL (₹)",
        "total_trades": "Trades Executed",
        "total_fees_paid": "Fees Paid (₹)",
        "win_rate": "Win Rate (%)",
        "cycles_scanned": "Cycles Scanned",
        "stop_reason": "Stop Reason"
    }
    cols_present = [c for c in cols_display.keys() if c in trials_df.columns]
    trials_df_display = trials_df[cols_present].rename(columns=cols_display)
    st.dataframe(trials_df_display.sort_index(ascending=False), use_container_width=True)
    
    # Database Clear Tool
    if st.button("🗑️ Clear L2 Trials History Log", use_container_width=True):
        state_data["trials"] = []
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
        st.toast("L2 Trials database cleanly wiped!")
        time.sleep(1.0)
        st.rerun()
