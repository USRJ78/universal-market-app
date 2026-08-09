# streamlit_app.py
import sys
import os

# Ensure local directory is in path for module loading
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st
import pandas as pd
import numpy as np
import json
import ccxt
import re
from datetime import datetime
import importlib

# Import daemon structures
import delta_demo_arb_bot
import delta_demo_geometry_bot
import swarm_bot_engine
import delta_demo_options_arb_bot
import stockfish_basis_arb_bot

importlib.reload(delta_demo_arb_bot)
importlib.reload(delta_demo_geometry_bot)
importlib.reload(swarm_bot_engine)
importlib.reload(delta_demo_options_arb_bot)
importlib.reload(stockfish_basis_arb_bot)

from delta_demo_arb_bot import STATE_FILE as ARB_STATE, LOG_FILE as ARB_LOG, DEMO_API, DEMO_SECRET, ENDPOINT
from delta_demo_geometry_bot import STATE_FILE as GEOM_STATE, LOG_FILE as GEOM_LOG
from swarm_bot_engine import STATE_FILE as SWARM_STATE, LOG_FILE as SWARM_LOG, ASSETS
from delta_demo_options_arb_bot import STATE_FILE as OPTIONS_STATE, LOG_FILE as OPTIONS_LOG
from stockfish_basis_arb_bot import STATE_FILE as STOCKFISH_STATE, LOG_FILE as STOCKFISH_LOG

st.set_page_config(
    page_title="Delta Exchange Trading Cockpit",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Obsidian & Violet Premium Styling (matching Delta theme)
st.markdown("""
<style>
    .reportview-container {
        background-color: #0b0e11;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(139, 92, 246, 0.4);
    }
    .status-active {
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid rgb(16, 185, 129);
        border-radius: 8px;
        padding: 8px;
        color: #10b981;
        font-weight: 700;
        text-align: center;
    }
    .status-inactive {
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid rgb(239, 68, 68);
        border-radius: 8px;
        padding: 8px;
        color: #ef4444;
        font-weight: 700;
        text-align: center;
    }
    .status-warning {
        background-color: rgba(245, 158, 11, 0.15);
        border: 1px solid rgb(245, 158, 11);
        border-radius: 8px;
        padding: 12px;
        color: #f59e0b;
        font-weight: 600;
    }
    .indicator-label {
        font-size: 12px;
        color: #94a3b8;
    }
    .indicator-value {
        font-size: 18px;
        font-weight: bold;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Delta Exchange Trading Cockpit")
st.markdown("Monitor account status and execute advanced algorithmic strategies on the **Delta India Testnet**.")

# ---------------------------------------------------------
# GLOBAL STATE & THREAD MANAGEMENT
# ---------------------------------------------------------
def check_pid_running(pid):
    if not pid:
        return False
    import subprocess
    try:
        if os.name == 'nt':
            output = subprocess.check_output(f"tasklist /FI \"PID eq {pid}\"", shell=True).decode('utf-8')
            return "PID" in output and str(pid) in output
        else:
            import os
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    except Exception:
        return False

def sync_daemon_state(state_path):
    if not os.path.exists(state_path):
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        return None
        
    is_active = False
    if state.get("is_running"):
        if state.get("starting"):
            is_active = True
        elif state.get("pid"):
            is_active = check_pid_running(state["pid"])
            
    if state.get("is_running") != is_active:
        state["is_running"] = is_active
        if not is_active:
            state["pid"] = None
            state["starting"] = False
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception:
            pass
    return state

# Sync all states
arb_state_data = sync_daemon_state(ARB_STATE)
geom_state_data = sync_daemon_state(GEOM_STATE)
swarm_state_data = sync_daemon_state(SWARM_STATE)
options_state_data = sync_daemon_state(OPTIONS_STATE)
stockfish_state_data = sync_daemon_state(STOCKFISH_STATE)

# Create defaults if files missing
if not arb_state_data:
    arb_state_data = {
        "is_running": False,
        "force_execute": False,
        "min_profit_pct": 0.15,
        "trade_size_usd": 100.0,
        "leverage": 20,
        "accumulated_profit_usd": 0.0,
        "trades": [],
        "last_update": datetime.now().isoformat()
    }
    with open(ARB_STATE, "w", encoding="utf-8") as f:
        json.dump(arb_state_data, f, indent=4)

if not geom_state_data:
    geom_state_data = {
        "is_running": False,
        "starting": False,
        "pid": None,
        "timeframe": "15m",
        "leverage": 15,
        "accumulated_profit_usd": 0.0,
        "trades": [],
        "active_position": None,
        "last_update": datetime.now().isoformat()
    }
    with open(GEOM_STATE, "w", encoding="utf-8") as f:
        json.dump(geom_state_data, f, indent=4)

if not swarm_state_data:
    swarm_state_data = {
        "is_running": False,
        "starting": False,
        "pid": None,
        "num_bots": 5000,
        "anomalies": [],
        "stats": {
            "total_scans": 0,
            "anomalies_detected": 0,
            "active_bugs": 0
        },
        "last_update": datetime.now().isoformat()
    }
    with open(SWARM_STATE, "w", encoding="utf-8") as f:
        json.dump(swarm_state_data, f, indent=4)

if not options_state_data:
    options_state_data = {
        "is_running": False,
        "force_execute": False,
        "min_profit_pct": 0.01,
        "trade_size_usd": 100.0,
        "leverage": 20,
        "accumulated_profit_usd": 0.0,
        "trades": [],
        "last_update": datetime.now().isoformat()
    }
    with open(OPTIONS_STATE, "w", encoding="utf-8") as f:
        json.dump(options_state_data, f, indent=4)

if not stockfish_state_data:
    stockfish_state_data = {
        "is_running": False,
        "starting": False,
        "force_execute": False,
        "min_profit_pct": 1.0,
        "trade_size_usd": 100.0,
        "leverage": 10,
        "accumulated_profit_usd": 0.0,
        "trades": [],
        "active_position": None,
        "last_update": datetime.now().isoformat()
    }
    with open(STOCKFISH_STATE, "w", encoding="utf-8") as f:
        json.dump(stockfish_state_data, f, indent=4)

# ---------------------------------------------------------
# EXCHANGE CONNECTION & CREDENTIALS CHECK
# ---------------------------------------------------------
is_authenticated = False
whitelisting_warning = ""
exchange_client = None
balance_data = {}

try:
    test_ex = ccxt.delta({
        'apiKey': DEMO_API,
        'secret': DEMO_SECRET,
        'enableRateLimit': True
    })
    test_ex.urls['api'] = {
        'public': ENDPOINT,
        'private': ENDPOINT
    }
    test_ex.load_markets()
    balance_data = test_ex.fetch_balance()
    is_authenticated = True
    exchange_client = test_ex
except Exception as e:
    err_str = str(e).lower()
    if "ip_not_whitelisted" in err_str:
        ip_match = re.search(r'"client_ip"\s*:\s*"([^"]+)"', str(e))
        whitelisting_warning = ip_match.group(1) if ip_match else "103.206.9.13"
    last_conn_error = str(e)

# ---------------------------------------------------------
# SIDEBAR PANEL: Account Connection Metrics
# ---------------------------------------------------------
st.sidebar.header("🔌 Account status")
if not is_authenticated:
    st.sidebar.markdown('<div class="status-inactive">🔴 CONNECTION FAILED</div>', unsafe_allow_html=True)
    if whitelisting_warning:
        st.sidebar.warning(f"⚠️ **IP Whitelisting Required!**\n\nYour API key is valid, but the current IP **`{whitelisting_warning}`** is not whitelisted in your Delta India Testnet settings. Add this IP to your key whitelist to activate trading.")
    else:
        st.sidebar.error(f"Connection Error: {last_conn_error}")
else:
    st.sidebar.markdown('<div class="status-active">🟢 TESTNET AUTHENTICATED</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("💼 Wallet Equity")

if is_authenticated and exchange_client:
    try:
        usdt_bal = balance_data.get("USDT", {}).get("free", 0.0)
        btc_bal = balance_data.get("BTC", {}).get("free", 0.0)
        eth_bal = balance_data.get("ETH", {}).get("free", 0.0)
        usd_bal = balance_data.get("USD", {}).get("free", 0.0)
        
        st.sidebar.metric("USD Margin Balance", f"${usd_bal:,.4f}")
        st.sidebar.metric("USDT Spot Balance", f"${usdt_bal:,.2f}")
        st.sidebar.metric("BTC Free Balance", f"{btc_bal:.6f} BTC")
        st.sidebar.metric("ETH Free Balance", f"{eth_bal:.6f} ETH")
    except Exception as e:
        st.sidebar.warning(f"Error reading wallet: {e}")
else:
    st.sidebar.info("Equity figures will load once IP is whitelisted.")

# ---------------------------------------------------------
# DASHBOARD TABS
# ---------------------------------------------------------
tab_arb, tab_geometry, tab_swarm, tab_options_arb, tab_stockfish_arb = st.tabs(["📐 Triangular Arbitrage", "📈 Market Geometry Retracement", "🐜 Swarm Bot Swarm", "📈 Options Arbitrage", "♚ Stockfish Arbitrage"])

# ==============================================================================
# TAB 1: TRIANGULAR ARBITRAGE SYSTEM
# ==============================================================================
with tab_arb:
    st.header("📐 Triangular Basis Arbitrage Scanner")
    st.markdown("Exploit price discrepancies between USD/USDT spots and perps sequentially.")
    
    is_arb_active = arb_state_data.get("is_running", False)
    
    col_ctrl, col_status = st.columns([2, 1])
    with col_ctrl:
        st.subheader("🛠️ Settings & Launch")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            min_profit_ui = st.slider(
                "Min Profit Trigger (%)",
                min_value=0.01,
                max_value=2.00,
                value=float(arb_state_data.get("min_profit_pct", 0.15)),
                step=0.01,
                key="arb_min_profit"
            )
            trade_size_ui = st.number_input(
                "Trade Size per Leg ($)",
                min_value=10.0,
                max_value=10000.0,
                value=float(arb_state_data.get("trade_size_usd", 100.0)),
                step=10.0,
                key="arb_trade_size"
            )
        with col_c2:
            leverage_ui = st.slider(
                "Swap Leverage Multiplier",
                min_value=1,
                max_value=50,
                value=int(arb_state_data.get("leverage", 20)),
                step=1,
                key="arb_leverage"
            )
            force_exec_ui = st.checkbox(
                "Force Execute on Next Ticks",
                value=bool(arb_state_data.get("force_execute", False)),
                key="arb_force"
            )
            
        # Update state on change
        if (min_profit_ui != arb_state_data.get("min_profit_pct") or
            trade_size_ui != arb_state_data.get("trade_size_usd") or
            leverage_ui != arb_state_data.get("leverage") or
            force_exec_ui != arb_state_data.get("force_execute")):
            arb_state_data["min_profit_pct"] = min_profit_ui
            arb_state_data["trade_size_usd"] = trade_size_ui
            arb_state_data["leverage"] = leverage_ui
            arb_state_data["force_execute"] = force_exec_ui
            with open(ARB_STATE, "w", encoding="utf-8") as f:
                json.dump(arb_state_data, f, indent=4)
                
    with col_status:
        st.subheader("🕹️ Operations Panel")
        if is_arb_active:
            st.markdown('<div class="status-active">🟢 ARB DAEMON RUNNING</div>', unsafe_allow_html=True)
            st.write(f"Process PID: `{arb_state_data.get('pid')}`")
            if st.button("🔴 STOP ARBITRAGE DAEMON", use_container_width=True, type="primary", key="stop_arb_btn"):
                arb_state_data["is_running"] = False
                with open(ARB_STATE, "w", encoding="utf-8") as f:
                    json.dump(arb_state_data, f, indent=4)
                st.toast("Arbitrage stop signal queued.")
                st.rerun()
        else:
            st.markdown('<div class="status-inactive">🔴 ARB DAEMON INACTIVE</div>', unsafe_allow_html=True)
            if st.button("🟢 LAUNCH ARBITRAGE DAEMON", use_container_width=True, disabled=(not is_authenticated), type="primary", key="launch_arb_btn"):
                arb_state_data["is_running"] = True
                arb_state_data["starting"] = True
                arb_state_data["pid"] = None
                with open(ARB_STATE, "w", encoding="utf-8") as f:
                    json.dump(arb_state_data, f, indent=4)
                    
                import subprocess
                subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "delta_demo_arb_bot.py"), "--start"],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                st.toast("Triangular Arb Daemon spawned.")
                st.rerun()

    st.markdown("---")
    
    # Spreads and prices scanner
    st.subheader("⚡ Live Arbitrage Spread Scan")
    
    public_ex = None
    try:
        pub = ccxt.delta({'enableRateLimit': True})
        pub.urls['api'] = {'public': ENDPOINT, 'private': ENDPOINT}
        pub.load_markets()
        public_ex = pub
    except Exception:
        pass
        
    if public_ex:
        try:
            tickers = public_ex.fetch_tickers(['BTC/USDT', 'ETH/USDT', 'BTC/USD:USD', 'ETH/USD:USD'])
            t_spot_btc = tickers.get('BTC/USDT', {})
            t_spot_eth = tickers.get('ETH/USDT', {})
            t_perp_btc = tickers.get('BTC/USD:USD', {})
            t_perp_eth = tickers.get('ETH/USD:USD', {})
            
            spot_btc_ask = t_spot_btc.get('ask') or t_spot_btc.get('last')
            spot_btc_bid = t_spot_btc.get('bid') or t_spot_btc.get('last')
            spot_eth_ask = t_spot_eth.get('ask') or t_spot_eth.get('last')
            spot_eth_bid = t_spot_eth.get('bid') or t_spot_eth.get('last')
            
            perp_btc_ask = t_perp_btc.get('ask', 0.0)
            perp_btc_bid = t_perp_btc.get('bid', 0.0)
            perp_eth_ask = t_perp_eth.get('ask', 0.0)
            perp_eth_bid = t_perp_eth.get('bid', 0.0)
            
            # Binance fallback for Spot if Testnet has zero depth
            if not spot_btc_ask or not spot_btc_bid or not spot_eth_ask or not spot_eth_bid:
                try:
                    binance = ccxt.binance()
                    bi_tickers = binance.fetch_tickers(['BTC/USDT', 'ETH/USDT'])
                    if not spot_btc_ask:
                        spot_btc_ask = bi_tickers['BTC/USDT']['ask']
                        spot_btc_bid = bi_tickers['BTC/USDT']['bid']
                    if not spot_eth_ask:
                        spot_eth_ask = bi_tickers['ETH/USDT']['ask']
                        spot_eth_bid = bi_tickers['ETH/USDT']['bid']
                except Exception:
                    pass
            
            # Spread yields
            if spot_btc_ask and perp_btc_bid and perp_eth_ask and spot_eth_bid:
                ret_A = (perp_btc_bid / spot_btc_ask) * (spot_eth_bid / perp_eth_ask) - 1.0
                net_ret_A = ret_A - 0.003
            else:
                ret_A = net_ret_A = 0.0
                
            if spot_eth_ask and perp_eth_bid and perp_btc_ask and spot_btc_bid:
                ret_B = (perp_eth_bid / spot_eth_ask) * (spot_btc_bid / perp_btc_ask) - 1.0
                net_ret_B = ret_B - 0.003
            else:
                ret_B = net_ret_B = 0.0
                
            o1, o2 = st.columns(2)
            with o1:
                color_A = "#10b981" if net_ret_A > 0 else "#94a3b8"
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.35); border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 8px; padding: 16px;">
                    <div style="font-size: 12px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">Triangular Spread Loop A (Spot Buy BTC ➔ Perp Sell BTC ➔ Perp Buy ETH ➔ Spot Sell ETH)</div>
                    <div style="font-size: 26px; font-weight: bold; color: {color_A}; margin-top: 6px;">Net Return: {net_ret_A*100:+.3f}%</div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 3px;">Gross Yield: {ret_A*100:+.3f}% | Taker Fees: -0.30%</div>
                </div>
                """, unsafe_allow_html=True)
            with o2:
                color_B = "#10b981" if net_ret_B > 0 else "#94a3b8"
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.35); border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 8px; padding: 16px;">
                    <div style="font-size: 12px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">Triangular Spread Loop B (Spot Buy ETH ➔ Perp Sell ETH ➔ Perp Buy BTC ➔ Spot Sell BTC)</div>
                    <div style="font-size: 26px; font-weight: bold; color: {color_B}; margin-top: 6px;">Net Return: {net_ret_B*100:+.3f}%</div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 3px;">Gross Yield: {ret_B*100:+.3f}% | Taker Fees: -0.30%</div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as ticker_err:
            st.warning(f"Unable to load spreads: {ticker_err}")
            
    st.markdown("---")
    
    st.subheader("📋 Output Logs Stream")
    if os.path.exists(ARB_LOG):
        try:
            with open(ARB_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()
            st.text_area("Recent arb bot activity:", value="".join(lines[-25:]), height=200, key="arb_log_stream")
        except Exception:
            st.caption("Logs unavailable.")
    else:
        st.caption("No logs recorded yet.")
        
    if st.button("🔄 Refresh Arb Console", use_container_width=True, key="refresh_arb_log"):
        st.rerun()
        
    st.markdown("---")
    
    st.subheader("📚 Completed Arbitrage Ledger")
    trades_arb = arb_state_data.get("trades", [])
    if not trades_arb:
        st.info("No completed arbitrage trades have been recorded.")
    else:
        df_arb = pd.DataFrame(trades_arb)
        cols = ["timestamp", "direction", "trade_size_usd", "net_return_pct", "profit_usd", "success"]
        df_arb_clean = df_arb[[c for c in cols if c in df_arb.columns]].copy()
        df_arb_clean.columns = [c.replace("_", " ").upper() for c in df_arb_clean.columns]
        st.dataframe(df_arb_clean, use_container_width=True)
        st.metric("Total Realized Arbitrage PnL", f"${arb_state_data.get('accumulated_profit_usd', 0.0):,.4f}")

# ==============================================================================
# TAB 2: MARKET GEOMETRY RETRACEMENT SYSTEM
# ==============================================================================
with tab_geometry:
    st.header("📈 Market Geometry Retracement strategy")
    st.markdown("Executes trend pullbacks and retracements relative to rolling Fibonacci channels.")
    
    is_geom_active = geom_state_data.get("is_running", False)
    active_pos = geom_state_data.get("active_position")
    
    col_gctrl, col_gstatus = st.columns([2, 1])
    with col_gctrl:
        st.subheader("🛠️ Settings & Launch")
        
        col_gc1, col_gc2 = st.columns(2)
        with col_gc1:
            timeframe_ui = st.selectbox(
                "Retracement Timeframe",
                options=["1m", "5m", "15m", "1h", "4h", "1d"],
                index=["1m", "5m", "15m", "1h", "4h", "1d"].index(geom_state_data.get("timeframe", "15m")),
                key="geom_timeframe"
            )
            geom_trade_size_ui = st.number_input(
                "Trade Size per Leg ($)",
                min_value=10.0,
                max_value=5000.0,
                value=float(geom_state_data.get("trade_size_usd", 100.0)),
                step=10.0,
                key="geom_trade_size"
            )
        with col_gc2:
            geom_leverage_ui = st.slider(
                "Futures Leverage (Margin Sizing)",
                min_value=1,
                max_value=50,
                value=int(geom_state_data.get("leverage", 15)),
                step=1,
                key="geom_leverage"
            )
            
        # Update state on change
        if (timeframe_ui != geom_state_data.get("timeframe") or
            geom_leverage_ui != geom_state_data.get("leverage") or
            geom_trade_size_ui != geom_state_data.get("trade_size_usd")):
            geom_state_data["timeframe"] = timeframe_ui
            geom_state_data["leverage"] = geom_leverage_ui
            geom_state_data["trade_size_usd"] = geom_trade_size_ui
            with open(GEOM_STATE, "w", encoding="utf-8") as f:
                json.dump(geom_state_data, f, indent=4)
                
    with col_gstatus:
        st.subheader("🕹️ Operations Panel")
        if is_geom_active:
            st.markdown('<div class="status-active">🟢 GEOMETRY DAEMON RUNNING</div>', unsafe_allow_html=True)
            st.write(f"Process PID: `{geom_state_data.get('pid')}`")
            if st.button("🔴 STOP GEOMETRY DAEMON", use_container_width=True, type="primary", key="stop_geom_btn"):
                geom_state_data["is_running"] = False
                with open(GEOM_STATE, "w", encoding="utf-8") as f:
                    json.dump(geom_state_data, f, indent=4)
                st.toast("Geometry stop signal queued.")
                st.rerun()
        else:
            st.markdown('<div class="status-inactive">🔴 GEOMETRY DAEMON INACTIVE</div>', unsafe_allow_html=True)
            if st.button("🟢 LAUNCH GEOMETRY DAEMON", use_container_width=True, disabled=(not is_authenticated), type="primary", key="launch_geom_btn"):
                geom_state_data["is_running"] = True
                geom_state_data["starting"] = True
                geom_state_data["pid"] = None
                with open(GEOM_STATE, "w", encoding="utf-8") as f:
                    json.dump(geom_state_data, f, indent=4)
                    
                import subprocess
                subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "delta_demo_geometry_bot.py"), "--start"],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                st.toast("Market Geometry Daemon spawned.")
                st.rerun()

    st.markdown("---")
    
    st.subheader("📊 Live Geometry Indicators")
    indicators = geom_state_data.get("indicators")
    if indicators:
        ind1, ind2, ind3, ind4 = st.columns(4)
        with ind1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">Last Ticker Price</div>
                <div class="indicator-value">${indicators.get('price', 0.0):,.2f}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Candle Open: ${indicators.get('open', 0.0):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with ind2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">20-Period Channel High</div>
                <div class="indicator-value" style="color: #ef4444;">${indicators.get('high20', 0.0):,.2f}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Resistance Boundary</div>
            </div>
            """, unsafe_allow_html=True)
        with ind3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">20-Period Channel Low</div>
                <div class="indicator-value" style="color: #10b981;">${indicators.get('low20', 0.0):,.2f}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Support Boundary</div>
            </div>
            """, unsafe_allow_html=True)
        with ind4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">Fib retracements (61.8% / 38.2%)</div>
                <div class="indicator-value" style="color: #8b5cf6;">${indicators.get('fib618', 0.0):,.1f} / ${indicators.get('fib382', 0.0):,.1f}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Long Support / Short Resistance</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Geometry indicators will load once the daemon scans the markets on the first cycle.")

    st.markdown("---")
    st.subheader("💼 Active Strategy Position")
    
    if active_pos:
        ap1, ap2, ap3, ap4 = st.columns(4)
        direction_label = "🔴 SHORT" if active_pos['direction'] == "SELL" else "🟢 LONG"
        pnl_val = active_pos.get('unrealized_pnl', 0.0)
        pnl_color = "#10b981" if pnl_val >= 0 else "#ef4444"
        
        with ap1:
            st.metric("Position Side & contracts", f"{direction_label} ({active_pos['qty']} contracts)")
        with ap2:
            st.metric("Entry Price / Current Price", f"${active_pos['fill_price']:,.2f} / ${active_pos.get('current_price', 0.0):,.2f}")
        with ap3:
            st.metric("Targets (TP / SL)", f"${active_pos['target_price']:,.2f} / ${active_pos['stop_price']:,.2f}")
        with ap4:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(139, 92, 246, 0.1); border-radius: 8px; padding: 12px; text-align: center;">
                <div style="font-size: 11px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">Net Unrealized Return</div>
                <div style="font-size: 20px; font-weight: bold; color: {pnl_color}; margin-top: 2px;">{pnl_val:+.4f} USD</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active position opened by the geometry bot.")

    st.markdown("---")
    
    st.subheader("📋 Output Logs Stream")
    if os.path.exists(GEOM_LOG):
        try:
            with open(GEOM_LOG, "r", encoding="utf-8") as f:
                geom_lines = f.readlines()
            st.text_area("Recent geometry bot activity:", value="".join(geom_lines[-25:]), height=200, key="geom_log_stream")
        except Exception:
            st.caption("Logs unavailable.")
    else:
        st.caption("No logs recorded yet.")
        
    if st.button("🔄 Refresh Geometry Console", use_container_width=True, key="refresh_geom_log"):
        st.rerun()

    st.markdown("---")
    
    st.subheader("📚 Completed Trade Ledger")
    trades_geom = geom_state_data.get("trades", [])
    if not trades_geom:
        st.info("No completed geometry trades have been recorded.")
    else:
        df_geom = pd.DataFrame(trades_geom)
        gcols = ["timestamp", "direction", "entry_price", "exit_price", "qty", "gross_pnl", "fees", "net_pnl", "exit_reason"]
        df_geom_clean = df_geom[[c for c in gcols if c in df_geom.columns]].copy()
        df_geom_clean.columns = [c.replace("_", " ").upper() for c in df_geom_clean.columns]
        st.dataframe(df_geom_clean, use_container_width=True)
        st.metric("Total Realized Geometry Strategy PnL", f"${geom_state_data.get('accumulated_profit_usd', 0.0):,.4f}")

# ==============================================================================
# TAB 3: SWARM BOT MULTI-ASSET PATTERN ANALYZER
# ==============================================================================
with tab_swarm:
    st.header("🐜 Swarm Bot Pattern Analyzer")
    st.markdown("Deploys a swarm of lightweight virtual worker bugs to crawl pattern variables across Crypto, Stocks, Bonds, and Indices.")
    
    is_swarm_active = swarm_state_data.get("is_running", False)
    
    col_sctrl, col_sstatus = st.columns([2, 1])
    with col_sctrl:
        st.subheader("🛠️ Deployment Settings")
        
        num_bots_ui = st.slider(
            "Swarm size (Active scanning Bugs)",
            min_value=100,
            max_value=10000,
            value=int(swarm_state_data.get("num_bots", 5000)),
            step=100,
            key="swarm_num_bots"
        )
        
        if num_bots_ui != swarm_state_data.get("num_bots"):
            swarm_state_data["num_bots"] = num_bots_ui
            with open(SWARM_STATE, "w", encoding="utf-8") as f:
                json.dump(swarm_state_data, f, indent=4)
                
    with col_sstatus:
        st.subheader("🕹️ Operations Control")
        if is_swarm_active:
            st.markdown('<div class="status-active">🟢 SWARM ACTIVE & CRAWLING</div>', unsafe_allow_html=True)
            st.write(f"Swarm PID: `{swarm_state_data.get('pid')}`")
            if st.button("🔴 DEACTIVATE PATTERN SWARM", use_container_width=True, type="primary", key="stop_swarm_btn"):
                swarm_state_data["is_running"] = False
                with open(SWARM_STATE, "w", encoding="utf-8") as f:
                    json.dump(swarm_state_data, f, indent=4)
                st.toast("Swarm stop queued.")
                st.rerun()
        else:
            st.markdown('<div class="status-inactive">🔴 SWARM DEACTIVATED</div>', unsafe_allow_html=True)
            if st.button("🟢 DEPLOY PATTERN SWARM", use_container_width=True, type="primary", key="launch_swarm_btn"):
                swarm_state_data["is_running"] = True
                swarm_state_data["starting"] = True
                swarm_state_data["pid"] = None
                with open(SWARM_STATE, "w", encoding="utf-8") as f:
                    json.dump(swarm_state_data, f, indent=4)
                    
                import subprocess
                subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "swarm_bot_engine.py"), "--start"],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                st.toast("Pattern Swarm Crawler deployed.")
                st.rerun()

    st.markdown("---")
    
    # Swarm statistics
    st.subheader("📊 Swarm Activity Indicators")
    stats = swarm_state_data.get("stats", {})
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Total Swarm Workers deployed", f"{stats.get('active_bugs', 0)} Bugs")
    with s2:
        st.metric("Total Scan Cycles completed", f"{stats.get('total_scans', 0)} cycles")
    with s3:
        st.metric("Pattern Anomalies detected", f"{stats.get('anomalies_detected', 0)} alerts")
        
    st.markdown("---")
    
    # Anomalies alerts table
    st.subheader("🚨 Live Anomalies & Pattern Alerts")
    anomalies = swarm_state_data.get("anomalies", [])
    if not anomalies:
        st.info("No active pattern anomalies have been flagged by the swarm yet. Launch the swarm to crawl markets.")
    else:
        df_anom = pd.DataFrame(anomalies)
        
        # Style direction column
        def highlight_direction(val):
            color = 'green' if val == 'BUY' else ('red' if val == 'SELL' else 'white')
            return f'color: {color}; font-weight: bold;'
            
        df_display = df_anom[["timestamp", "bug_id", "asset", "pattern", "direction", "price", "strength"]].copy()
        df_display.columns = [c.replace("_", " ").upper() for c in df_display.columns]
        
        st.dataframe(df_display, use_container_width=True)
        
    st.markdown("---")
    
    # Swarm logs
    st.subheader("📋 Output Logs Stream")
    if os.path.exists(SWARM_LOG):
        try:
            with open(SWARM_LOG, "r", encoding="utf-8") as f:
                swarm_lines = f.readlines()
            st.text_area("Recent swarm crawler activity:", value="".join(swarm_lines[-25:]), height=200, key="swarm_log_stream")
        except Exception:
            st.caption("Logs unavailable.")
    else:
        st.caption("No logs recorded yet.")
        
    if st.button("🔄 Refresh Swarm Console", use_container_width=True, key="refresh_swarm_log"):
        st.rerun()

# ==============================================================================
# TAB 4: OPTIONS ARBITRAGE SYSTEM
# ==============================================================================
with tab_options_arb:
    st.header("📈 Options Put-Call Parity Arbitrage")
    st.markdown("Exploit Put-Call Parity pricing discrepancies on Delta Exchange options.")
    
    is_options_active = options_state_data.get("is_running", False)
    
    col_octrl, col_ostatus = st.columns([2, 1])
    with col_octrl:
        st.subheader("🛠️ Strategy Settings")
        
        col_oc1, col_oc2 = st.columns(2)
        with col_oc1:
            min_profit_opt = st.slider(
                "Min profit target (%)",
                min_value=0.001,
                max_value=2.0,
                value=float(options_state_data.get("min_profit_pct", 0.01)),
                step=0.001,
                format="%.3f%%",
                key="options_min_profit"
            )
            trade_size_opt = st.number_input(
                "Trade size per leg ($)",
                min_value=10.0,
                max_value=10000.0,
                value=float(options_state_data.get("trade_size_usd", 100.0)),
                step=10.0,
                key="options_trade_size"
            )
        with col_oc2:
            leverage_opt = st.slider(
                "Margin leverage",
                min_value=1,
                max_value=50,
                value=int(options_state_data.get("leverage", 20)),
                step=1,
                key="options_leverage"
            )
            force_exec_opt = st.checkbox(
                "Force execute best spread",
                value=bool(options_state_data.get("force_execute", False)),
                key="options_force"
            )
            auto_unwind_opt = st.checkbox(
                "Auto-Unwind active position early for profit",
                value=bool(options_state_data.get("auto_unwind", True)),
                key="options_auto_unwind"
            )
            
        # Save state if changed
        if (min_profit_opt != options_state_data.get("min_profit_pct") or
            trade_size_opt != options_state_data.get("trade_size_usd") or
            leverage_opt != options_state_data.get("leverage") or
            force_exec_opt != options_state_data.get("force_execute") or
            auto_unwind_opt != options_state_data.get("auto_unwind", True)):
            options_state_data["min_profit_pct"] = min_profit_opt
            options_state_data["trade_size_usd"] = trade_size_opt
            options_state_data["leverage"] = leverage_opt
            options_state_data["force_execute"] = force_exec_opt
            options_state_data["auto_unwind"] = auto_unwind_opt
            with open(OPTIONS_STATE, "w", encoding="utf-8") as f:
                json.dump(options_state_data, f, indent=4)
                
    with col_ostatus:
        st.subheader("🕹️ Operations Control")
        if is_options_active:
            st.markdown('<div class="status-active">🟢 OPTIONS DAEMON RUNNING</div>', unsafe_allow_html=True)
            st.write(f"Process PID: `{options_state_data.get('pid')}`")
            if st.button("🔴 STOP OPTIONS DAEMON", use_container_width=True, type="primary", key="stop_options_btn"):
                options_state_data["is_running"] = False
                with open(OPTIONS_STATE, "w", encoding="utf-8") as f:
                    json.dump(options_state_data, f, indent=4)
                st.toast("Options stop signal queued.")
                st.rerun()
        else:
            st.markdown('<div class="status-inactive">🔴 OPTIONS DAEMON INACTIVE</div>', unsafe_allow_html=True)
            if st.button("🟢 LAUNCH OPTIONS DAEMON", use_container_width=True, disabled=(not is_authenticated), type="primary", key="launch_options_btn"):
                options_state_data["is_running"] = True
                options_state_data["starting"] = True
                options_state_data["pid"] = None
                with open(OPTIONS_STATE, "w", encoding="utf-8") as f:
                    json.dump(options_state_data, f, indent=4)
                    
                import subprocess
                subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "delta_demo_options_arb_bot.py"), "--start"],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                st.toast("Options Arbitrage Daemon spawned.")
                st.rerun()

    st.markdown("---")
    
    # Live scanner table
    st.subheader("📊 Live Options Parity Violations Scan")
    
    if exchange_client:
        try:
            # Let's perform a fast local scan of parity opportunities
            options_by_key = {}
            for symbol, m in exchange_client.markets.items():
                if m.get('option'):
                    underlying = m.get('underlying') or m.get('base')
                    if underlying in ['BTC', 'ETH']:
                        expiry = m.get('expiryDatetime')
                        strike = m.get('strike')
                        opt_type = m.get('optionType')
                        if expiry and strike is not None and opt_type:
                            expiry_str = expiry.split('T')[0]
                            key = (underlying, expiry_str, strike)
                            if key not in options_by_key:
                                options_by_key[key] = {}
                            options_by_key[key][opt_type] = symbol
            
            # Fetch tickers
            tickers = exchange_client.fetch_tickers()
            
            opportunities = []
            for (underlying, expiry_str, strike), pair in options_by_key.items():
                call_symbol = pair.get('call')
                put_symbol = pair.get('put')
                if not call_symbol or not put_symbol:
                    continue
                
                c_ticker = tickers.get(call_symbol)
                p_ticker = tickers.get(put_symbol)
                if not c_ticker or not p_ticker:
                    continue
                
                c_bid = c_ticker.get('bid')
                c_ask = c_ticker.get('ask')
                p_bid = p_ticker.get('bid')
                p_ask = p_ticker.get('ask')
                
                if c_bid is None or c_ask is None or p_bid is None or p_ask is None:
                    continue
                    
                perp_symbol = 'BTC/USD:USD' if underlying == 'BTC' else 'ETH/USD:USD'
                u_ticker = tickers.get(perp_symbol)
                if not u_ticker or u_ticker.get('bid') is None or u_ticker.get('ask') is None:
                    continue
                
                u_bid = u_ticker['bid']
                u_ask = u_ticker['ask']
                
                profit_A = p_bid - c_ask + u_bid - strike
                pct_A = profit_A / u_bid * 100
                
                profit_B = c_bid - p_ask - u_ask + strike
                pct_B = profit_B / u_ask * 100
                
                net_A = pct_A - 0.11
                net_B = pct_B - 0.11
                
                if net_A > 0:
                    opportunities.append({
                        "Asset": underlying,
                        "Expiry": expiry_str,
                        "Strike": strike,
                        "Type": "Loop A (Buy Call/Sell Put/Short Perp)",
                        "Gross Yield": f"{pct_A:+.3f}%",
                        "Net Return": f"{net_A:+.3f}%",
                        "USD Profit/Unit": f"${profit_A:+.2f}",
                        "raw_val": net_A
                    })
                if net_B > 0:
                    opportunities.append({
                        "Asset": underlying,
                        "Expiry": expiry_str,
                        "Strike": strike,
                        "Type": "Loop B (Sell Call/Buy Put/Long Perp)",
                        "Gross Yield": f"{pct_B:+.3f}%",
                        "Net Return": f"{net_B:+.3f}%",
                        "USD Profit/Unit": f"${profit_B:+.2f}",
                        "raw_val": net_B
                    })
            
            if opportunities:
                df_opp = pd.DataFrame(opportunities)
                df_opp = df_opp.sort_values("raw_val", ascending=False).drop(columns=["raw_val"])
                st.dataframe(df_opp, use_container_width=True)
            else:
                st.info("No active Put-Call Parity violations found exceeding transaction fees (0.11%) at the moment.")
                
        except Exception as scan_err:
            st.warning(f"Unable to load active spreads scan: {scan_err}")
    else:
        st.info("Scanner requires Delta exchange client credentials.")
        
    st.markdown("---")
    
    # Active Positions
    st.subheader("💼 Active Options Arbitrage Positions")
    
    # 1. Check if tracking active position in state file
    tracked_pos = options_state_data.get("active_position")
    if tracked_pos and exchange_client:
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 12px; padding: 18px; margin-bottom: 20px;">
            <div style="font-size: 14px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">Active Strategy Tracked Position</div>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div><b>Asset</b>: """ + str(tracked_pos['underlying']) + """</div>
                <div><b>Loop Type</b>: Loop """ + str(tracked_pos['loop']) + """</div>
                <div><b>Strike</b>: """ + str(tracked_pos['strike']) + """</div>
                <div><b>Expiry</b>: """ + str(tracked_pos['expiry']) + """</div>
                <div><b>Size</b>: """ + str(tracked_pos['qty']) + """ contracts</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate real-time profit for tracking
        try:
            perp_sym = tracked_pos["legs"]["perp"]["symbol"]
            call_sym = tracked_pos["legs"]["call"]["symbol"]
            put_sym = tracked_pos["legs"]["put"]["symbol"]
            
            t_curr = exchange_client.fetch_tickers([perp_sym, call_sym, put_sym])
            c_tick, p_tick, u_tick = t_curr.get(call_sym), t_curr.get(put_sym), t_curr.get(perp_sym)
            
            if c_tick and p_tick and u_tick:
                c_bid = c_tick.get('bid') or c_tick.get('last')
                c_ask = c_tick.get('ask') or c_tick.get('last')
                p_bid = p_tick.get('bid') or p_tick.get('last')
                p_ask = p_tick.get('ask') or p_tick.get('last')
                u_bid = u_tick.get('bid') or u_tick.get('last')
                u_ask = u_tick.get('ask') or u_tick.get('last')
                
                market_perp = exchange_client.market(perp_sym)
                contract_size = market_perp.get('contractSize') or 1.0
                total_units = tracked_pos["qty"] * contract_size
                
                if tracked_pos["loop"] == "A":
                    entry_cost_unit = tracked_pos["legs"]["call"]["entry_price"] - tracked_pos["legs"]["put"]["entry_price"] - tracked_pos["legs"]["perp"]["entry_price"]
                    exit_val_unit = c_bid - p_ask - u_ask
                else:
                    entry_cost_unit = tracked_pos["legs"]["put"]["entry_price"] - tracked_pos["legs"]["call"]["entry_price"] + tracked_pos["legs"]["perp"]["entry_price"]
                    exit_val_unit = p_bid - c_ask + u_bid
                    
                gross_pnl = (exit_val_unit - entry_cost_unit) * total_units
                est_exit_fees = total_units * u_ask * 0.0011
                net_pnl = gross_pnl - est_exit_fees
                
                pnl_color = "#10b981" if net_pnl >= 0 else "#ef4444"
                
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.35); border: 1px solid rgba(139, 92, 246, 0.15); border-radius: 8px; padding: 15px; margin-bottom: 20px; text-align: center;">
                    <div style="font-size: 11px; color: #94a3b8; font-weight: bold; text-transform: uppercase;">Unrealized Day Trade Returns</div>
                    <div style="font-size: 24px; font-weight: bold; color: {pnl_color}; margin-top: 4px;">{net_pnl:+.4f} USD</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 3px;">Gross PnL: {gross_pnl:+.4f} USD | Unwind Fees: -{est_exit_fees:.4f} USD</div>
                </div>
                """, unsafe_allow_html=True)
                
            col_unwind_btn, _ = st.columns([1, 1])
            with col_unwind_btn:
                if st.button("🔴 MANUAL UNWIND POSITION EARLY", use_container_width=True, key="options_manual_unwind"):
                    with st.spinner("Placing early unwinding orders on exchange..."):
                        qty = tracked_pos["qty"]
                        unwind_success = True
                        unwind_orders = []
                        try:
                            if tracked_pos["loop"] == "A":
                                # Unwind Loop A: Sell Call, Buy Put, Buy Perp
                                o_p = exchange_client.create_market_buy_order(perp_sym, qty, params={'reduceOnly': True})
                                unwind_orders.append(o_p)
                                o_c = exchange_client.create_market_sell_order(call_sym, qty, params={'reduceOnly': True})
                                unwind_orders.append(o_c)
                                o_pt = exchange_client.create_market_buy_order(put_sym, qty, params={'reduceOnly': True})
                                unwind_orders.append(o_pt)
                            else:
                                # Unwind Loop B: Buy Call, Sell Put, Sell Perp
                                o_p = exchange_client.create_market_sell_order(perp_sym, qty, params={'reduceOnly': True})
                                unwind_orders.append(o_p)
                                o_c = exchange_client.create_market_buy_order(call_sym, qty, params={'reduceOnly': True})
                                unwind_orders.append(o_c)
                                o_pt = exchange_client.create_market_sell_order(put_sym, qty, params={'reduceOnly': True})
                                unwind_orders.append(o_pt)
                                
                            st.toast("Unwind orders filled successfully!")
                        except Exception as unwind_ex:
                            st.error(f"Unwind orders placement failed: {unwind_ex}")
                            unwind_success = False
                            
                        if len(unwind_orders) > 0:
                            # Record closed trade in state
                            unwind_trade = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "loop": tracked_pos["loop"],
                                "underlying": tracked_pos["underlying"],
                                "expiry": tracked_pos["expiry"],
                                "strike": tracked_pos["strike"],
                                "qty": qty,
                                "net_return_pct": (net_pnl / (total_units * u_ask)) * 100 if 'net_pnl' in locals() else 0.0,
                                "profit_usd": net_pnl if unwind_success and 'net_pnl' in locals() else 0.0,
                                "success": unwind_success,
                                "type": "MANUAL_CLOSE",
                                "legs": [
                                    {
                                        "symbol": o.get("symbol", "N/A"),
                                        "side": o.get("side", "N/A"),
                                        "amount": o.get("amount", 0.0),
                                        "price": o.get("average", o.get("price", 0.0)),
                                        "id": o.get("id", "N/A")
                                    } for o in unwind_orders
                                ]
                            }
                            
                            options_state_data["trades"].append(unwind_trade)
                            options_state_data["active_position"] = None
                            if unwind_success and 'net_pnl' in locals():
                                options_state_data["accumulated_profit_usd"] += net_pnl
                            with open(OPTIONS_STATE, "w", encoding="utf-8") as f:
                                json.dump(options_state_data, f, indent=4)
                            st.rerun()
        except Exception as unwind_calc_err:
            st.warning(f"Error computing active position realtime returns: {unwind_calc_err}")
            
    if exchange_client:
        try:
            positions = exchange_client.fetch_positions()
            active_options_pos = []
            for pos in positions:
                size = abs(float(pos.get('contracts') or pos.get('size', 0)))
                symbol = pos.get('symbol', '')
                if size != 0 and ('-' in symbol or symbol in ['BTC/USD:USD', 'ETH/USD:USD']):
                    active_options_pos.append(pos)
                    
            if active_options_pos:
                df_pos = pd.DataFrame(active_options_pos)
                pcols = ["symbol", "side", "contracts", "entryPrice", "markPrice", "unrealizedPnl"]
                df_pos_clean = df_pos[[c for c in pcols if c in df_pos.columns]].copy()
                df_pos_clean.columns = [c.replace("_", " ").upper() for c in df_pos_clean.columns]
                st.dataframe(df_pos_clean, use_container_width=True)
            else:
                st.info("No active exchange positions open.")
        except Exception as pos_err:
            st.warning(f"Unable to fetch positions: {pos_err}")
            
    st.markdown("---")
    
    # Output logs
    st.subheader("📋 Output Logs Stream")
    if os.path.exists(OPTIONS_LOG):
        try:
            with open(OPTIONS_LOG, "r", encoding="utf-8") as f:
                opt_lines = f.readlines()
            st.text_area("Recent options bot activity:", value="".join(opt_lines[-25:]), height=200, key="options_log_stream")
        except Exception:
            st.caption("Logs unavailable.")
    else:
        st.caption("No logs recorded yet.")
        
    if st.button("🔄 Refresh Options Console", use_container_width=True, key="refresh_options_log"):
        st.rerun()
        
    st.markdown("---")
    
    # Ledger of trades
    st.subheader("📚 Completed Options Arbitrage Ledger")
    trades_options = options_state_data.get("trades", [])
    if not trades_options:
        st.info("No completed options arbitrage trades have been recorded.")
    else:
        df_opt_ledger = pd.DataFrame(trades_options)
        cols_ol = ["timestamp", "loop", "underlying", "expiry", "strike", "qty", "net_return_pct", "profit_usd", "success"]
        df_opt_clean = df_opt_ledger[[c for c in cols_ol if c in df_opt_ledger.columns]].copy()
        df_opt_clean.columns = [c.replace("_", " ").upper() for c in df_opt_clean.columns]
        st.dataframe(df_opt_clean, use_container_width=True)
        st.metric("Total Realized Options Arbitrage PnL", f"${options_state_data.get('accumulated_profit_usd', 0.0):,.4f}")

# ==============================================================================
# TAB 5: STOCKFISH BASIS ARBITRAGE SYSTEM
# ==============================================================================
with tab_stockfish_arb:
    st.header("♚ Stockfish-Guided Basis Arbitrage Scanner")
    st.markdown("Exploit perpetual swap basis spreads using FEN chess board mappings and Stockfish valuations.")
    
    is_sf_active = stockfish_state_data.get("is_running", False)
    active_sf_pos = stockfish_state_data.get("active_position")
    
    col_sfctrl, col_sfstatus = st.columns([2, 1])
    with col_sfctrl:
        st.subheader("🛠️ Settings & Launch")
        
        col_sfc1, col_sfc2 = st.columns(2)
        with col_sfc1:
            sf_trigger_ui = st.slider(
                "Min Stockfish Score Trigger",
                min_value=0.5,
                max_value=3.0,
                value=float(stockfish_state_data.get("min_profit_pct", 1.0)),
                step=0.1,
                key="sf_min_score"
            )
            sf_trade_size_ui = st.number_input(
                "Trade Size per Leg ($)",
                min_value=10.0,
                max_value=5000.0,
                value=float(stockfish_state_data.get("trade_size_usd", 100.0)),
                step=10.0,
                key="sf_trade_size"
            )
        with col_sfc2:
            sf_leverage_ui = st.slider(
                "Futures Leverage Multiplier",
                min_value=1,
                max_value=50,
                value=int(stockfish_state_data.get("leverage", 10)),
                step=1,
                key="sf_leverage"
            )
            sf_force_exec_ui = st.checkbox(
                "Force Execute Next Tick",
                value=bool(stockfish_state_data.get("force_execute", False)),
                key="sf_force"
            )
            
        # Update state on change
        if (sf_trigger_ui != stockfish_state_data.get("min_profit_pct") or
            sf_trade_size_ui != stockfish_state_data.get("trade_size_usd") or
            sf_leverage_ui != stockfish_state_data.get("leverage") or
            sf_force_exec_ui != stockfish_state_data.get("force_execute")):
            stockfish_state_data["min_profit_pct"] = sf_trigger_ui
            stockfish_state_data["trade_size_usd"] = sf_trade_size_ui
            stockfish_state_data["leverage"] = sf_leverage_ui
            stockfish_state_data["force_execute"] = sf_force_exec_ui
            with open(STOCKFISH_STATE, "w", encoding="utf-8") as f:
                json.dump(stockfish_state_data, f, indent=4)
                
    with col_sfstatus:
        st.subheader("🕹️ Operations Panel")
        if is_sf_active:
            st.markdown('<div class="status-active">🟢 STOCKFISH DAEMON RUNNING</div>', unsafe_allow_html=True)
            st.write(f"Process PID: `{stockfish_state_data.get('pid')}`")
            if st.button("🔴 STOP STOCKFISH DAEMON", use_container_width=True, type="primary", key="stop_sf_btn"):
                stockfish_state_data["is_running"] = False
                with open(STOCKFISH_STATE, "w", encoding="utf-8") as f:
                    json.dump(stockfish_state_data, f, indent=4)
                st.toast("Stockfish stop signal queued.")
                st.rerun()
        else:
            st.markdown('<div class="status-inactive">🔴 STOCKFISH DAEMON INACTIVE</div>', unsafe_allow_html=True)
            if st.button("🟢 LAUNCH STOCKFISH DAEMON", use_container_width=True, disabled=(not is_authenticated), type="primary", key="launch_sf_btn"):
                stockfish_state_data["is_running"] = True
                stockfish_state_data["starting"] = True
                stockfish_state_data["pid"] = None
                with open(STOCKFISH_STATE, "w", encoding="utf-8") as f:
                    json.dump(stockfish_state_data, f, indent=4)
                    
                import subprocess
                subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "stockfish_basis_arb_bot.py"), "--start"],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                st.toast("Stockfish Basis Arb Daemon spawned.")
                st.rerun()

    st.markdown("---")
    
    st.subheader("📊 Stockfish Board & Market Scanner")
    sf_ind = stockfish_state_data.get("indicators")
    if sf_ind:
        si1, si2, si3, si4 = st.columns(4)
        with si1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">BTC Spot Ask / Perp Bid</div>
                <div class="indicator-value">${sf_ind.get('spot_ask', 0.0):,.2f} / ${sf_ind.get('perp_bid', 0.0):,.2f}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Basis: {sf_ind.get('basis_spread_pct', 0.0):+.4f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with si2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">Funding Rate APR / Volatility</div>
                <div class="indicator-value" style="color: #8b5cf6;">{sf_ind.get('funding_rate_apr', 0.0):+.2f}% / {sf_ind.get('volatility_annual', 0.0)*100:.1f}%</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Chess Position Mapped</div>
            </div>
            """, unsafe_allow_html=True)
        with si3:
            import urllib.parse
            board_url = f"https://lichess.org/editor/{urllib.parse.quote(sf_ind.get('fen', ''))}"
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">Stockfish Mapped FEN</div>
                <div style="font-family: monospace; font-size: 11px; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 6px;">{sf_ind.get('fen', 'N/A')}</div>
                <div style="font-size: 11px; margin-top: 5px;"><a href="{board_url}" target="_blank" style="color: #8b5cf6; text-decoration: none; font-weight: bold;">♟️ View on Lichess</a></div>
            </div>
            """, unsafe_allow_html=True)
        with si4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="indicator-label">Stockfish Score / Best Move</div>
                <div class="indicator-value" style="color: #10b981;">{sf_ind.get('score', 0.0):+.2f}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Recommended: {sf_ind.get('bestmove', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Stockfish board metrics will load once the daemon completes its first scan loop.")

    st.markdown("---")
    st.subheader("💼 Active Arbitrage Position")
    if active_sf_pos:
        as1, as2, as3, as4 = st.columns(4)
        dir_lbl = "🟢 LONG BASIS (BUY PERP)" if active_sf_pos["direction"] == "BUY" else "🔴 SHORT BASIS (SELL PERP)"
        with as1:
            st.metric("Position Side & Size", f"{dir_lbl} ({active_sf_pos['qty']} contracts)")
        with as2:
            st.metric("Perp Entry Price", f"${active_sf_pos['fill_price']:,.2f}")
        with as3:
            st.metric("Spot Entry Price", f"${active_sf_pos['spot_price']:,.2f}")
        with as4:
            mode_label = "SANDBOX" if active_sf_pos.get("is_sandbox") else "LIVE EXCHANGE"
            st.metric("Execution Mode", mode_label)
            
        # Funding Lock Status Row
        st.markdown("##### 🔒 Funding Lock Status")
        import time
        now_ts = time.time()
        next_funding_ts = active_sf_pos.get("next_funding_timestamp", 0)
        next_funding_ist = active_sf_pos.get("next_funding_time_ist", "N/A")
        
        lock_col1, lock_col2, lock_col3 = st.columns([1.2, 1.4, 1.4])
        with lock_col1:
            if now_ts < next_funding_ts + 15:
                st.markdown('<span style="color: #ef4444; font-weight: bold; font-size: 16px;">🔒 LOCKED (Hold till funding)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span style="color: #10b981; font-weight: bold; font-size: 16px;">🔓 UNLOCKED (Funding passed)</span>', unsafe_allow_html=True)
        with lock_col2:
            st.markdown(f"**Next Funding Epoch:** `{next_funding_ist}`")
        with lock_col3:
            if now_ts < next_funding_ts:
                rem_sec = int(next_funding_ts - now_ts)
                hours = rem_sec // 3600
                minutes = (rem_sec % 3600) // 60
                st.markdown(f"**Time Remaining:** `{hours}h {minutes}m`")
            else:
                st.markdown("**Time Remaining:** `0h 0m (Passed)`")
                
        st.markdown(" ")
        if st.button("🔴 Force Close Position Manually", use_container_width=True, key="manual_close_sf_pos"):
            with st.spinner("Executing manual close of Stockfish Basis Arbitrage legs..."):
                try:
                    # Load the state
                    with open(STOCKFISH_STATE, "r", encoding="utf-8") as f:
                        state_data = json.load(f)
                    
                    active_pos = state_data.get("active_position")
                    if active_pos:
                        qty = active_pos["qty"]
                        dir_side = active_pos["direction"]
                        is_sandbox = active_pos.get("is_sandbox", True)
                        
                        exit_price = active_pos["fill_price"]
                        exit_spot = active_pos["spot_price"]
                        
                        # 1. Fetch live market tickers to compute PnL if possible
                        try:
                            tickers = exchange_client.fetch_tickers(['BTC/USDT', 'BTC/USD:USD']) if exchange_client else {}
                            t_spot = tickers.get('BTC/USDT')
                            t_perp = tickers.get('BTC/USD:USD')
                            if t_perp:
                                exit_price = t_perp.get('ask') if dir_side == "SELL" else t_perp.get('bid')
                            if t_spot:
                                exit_spot = t_spot.get('bid') if dir_side == "SELL" else t_spot.get('ask')
                        except Exception:
                            pass
                            
                        # 2. Place close orders if not sandbox
                        if not is_sandbox and exchange_client:
                            try:
                                if dir_side == "SELL":
                                    order = exchange_client.create_market_buy_order('BTC/USD:USD', qty)
                                else:
                                    order = exchange_client.create_market_sell_order('BTC/USD:USD', qty)
                                exit_price = order.get('average', order.get('price', exit_price))
                            except Exception as ex:
                                st.error(f"Error placing live close order on exchange: {ex}. Falling back to virtual close.")
                        
                        # 3. Calculate PnL and append to trades
                        if dir_side == "SELL":
                            perp_pnl = (active_pos["fill_price"] - exit_price) * 0.001 * qty
                            spot_pnl = (exit_spot - active_pos["spot_price"]) * 0.001 * qty
                        else:
                            perp_pnl = (exit_price - active_pos["fill_price"]) * 0.001 * qty
                            spot_pnl = (active_pos["spot_price"] - exit_spot) * 0.001 * qty
                            
                        nominal_val = qty * 0.001 * active_pos["fill_price"]
                        fees = nominal_val * 0.003
                        net_profit = perp_pnl + spot_pnl - fees
                        
                        trade_record = {
                            "timestamp_entry": active_pos["timestamp"],
                            "timestamp_exit": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "direction": dir_side,
                            "qty": qty,
                            "entry_perp": active_pos["fill_price"],
                            "exit_perp": exit_price,
                            "entry_spot": active_pos["spot_price"],
                            "exit_spot": exit_spot,
                            "fees_usd": fees,
                            "net_profit_usd": net_profit,
                            "is_sandbox": is_sandbox
                        }
                        
                        state_data["trades"].append(trade_record)
                        state_data["accumulated_profit_usd"] += net_profit
                        state_data["active_position"] = None
                        
                        # Save state
                        with open(STOCKFISH_STATE, "w", encoding="utf-8") as f:
                            json.dump(state_data, f, indent=4)
                        
                        # Append to log
                        try:
                            with open(STOCKFISH_LOG, "a", encoding="utf-8") as lf:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                lf.write(f"[{timestamp}] 🔴 MANUAL CLOSE TRIGGERED via Streamlit. Net PnL: {net_profit:+.4f} USD\n")
                        except Exception:
                            pass
                            
                        st.success(f"Position closed successfully! Net PnL: ${net_profit:+.4f}")
                        st.rerun()
                except Exception as err:
                    st.error(f"Error executing manual close: {err}")
    else:
        st.info("No active arbitrage positions open.")

    st.markdown("---")
    st.subheader("📋 Output Logs Stream")
    if os.path.exists(STOCKFISH_LOG):
        try:
            with open(STOCKFISH_LOG, "r", encoding="utf-8") as f:
                sf_lines = f.readlines()
            st.text_area("Recent Stockfish bot activity:", value="".join(sf_lines[-25:]), height=200, key="sf_log_stream")
        except Exception:
            st.caption("Logs unavailable.")
    else:
        st.caption("No logs recorded yet.")
        
    if st.button("🔄 Refresh Stockfish Console", use_container_width=True, key="refresh_sf_log"):
        st.rerun()

    st.markdown("---")
    st.subheader("📚 Completed Stockfish Arbitrage Ledger")
    trades_sf = stockfish_state_data.get("trades", [])
    if not trades_sf:
        st.info("No completed Stockfish basis arbitrage trades have been recorded.")
    else:
        df_sf_ledger = pd.DataFrame(trades_sf)
        cols_sf = ["timestamp_entry", "timestamp_exit", "direction", "qty", "entry_perp", "exit_perp", "entry_spot", "exit_spot", "net_profit_usd"]
        df_sf_clean = df_sf_ledger[[c for c in cols_sf if c in df_sf_ledger.columns]].copy()
        df_sf_clean.columns = [c.replace("_", " ").upper() for c in df_sf_clean.columns]
        st.dataframe(df_sf_clean, use_container_width=True)
        st.metric("Total Realized Stockfish PnL", f"${stockfish_state_data.get('accumulated_profit_usd', 0.0):,.4f}")

