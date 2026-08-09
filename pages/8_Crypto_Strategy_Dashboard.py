# pages/8_Crypto_Strategy_Dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import importlib
import crypto_strategy_helper

# Force reload of helper to prevent Streamlit caching old python scripts
importlib.reload(crypto_strategy_helper)
from crypto_strategy_helper import CryptoStrategyHelper

st.set_page_config(
    page_title="Crypto Multi-Strategy Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphic Violet styling for a premium crypto feel
st.markdown("""
<style>
    .metric-card {
        background: rgba(124, 58, 237, 0.08);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(139, 92, 246, 0.2);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        border: 1px solid rgba(167, 139, 250, 0.4);
        background: rgba(124, 58, 237, 0.12);
    }
    .metric-title {
        color: rgba(255, 255, 255, 0.7);
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
    }
    .section-header {
        font-size: 22px;
        font-weight: 600;
        color: #ffffff;
        margin-top: 24px;
        margin-bottom: 12px;
        border-bottom: 2px solid rgba(139, 92, 246, 0.2);
        padding-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🪙 Crypto Quantitative Multi-Strategy Dashboard")
st.markdown("Run backtest simulations of core trading models adapted for cryptocurrency baskets. Evaluate, blend, and explore trade metrics dynamically.")

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Backtest Controls")

selected_coins = st.sidebar.multiselect(
    "Select Crypto Basket",
    ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "LINK", "LTC", "AVAX"],
    default=["BTC", "ETH", "SOL"],
    help="Select assets to run individual and basket strategy simulations."
)

col_s, col_e = st.sidebar.columns(2)
with col_s:
    start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=730))
with col_e:
    end_date = st.sidebar.date_input("End Date", datetime.now())

starting_capital = st.sidebar.number_input("Starting Capital ($)", min_value=100.0, value=100000.0, step=5000.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Strategy Parameters")

atr_period = st.sidebar.slider("ATR Period", min_value=1, max_value=30, value=10)
ut_mult = st.sidebar.slider("ATR Multiplier", min_value=0.5, max_value=5.0, value=1.0, step=0.1)

fee_pct = st.sidebar.number_input("Taker Fee (%)", min_value=0.0, max_value=2.0, value=0.10, step=0.05) / 100.0
slip_pct = st.sidebar.number_input("Slippage (%)", min_value=0.0, max_value=2.0, value=0.05, step=0.05) / 100.0

if not selected_coins:
    st.info("👈 Please select at least one cryptocurrency in the sidebar to run simulations.")
    st.stop()

# Helper instance
helper = CryptoStrategyHelper()

# Cache data loading to prevent redundant downloads
@st.cache_data
def get_processed_data(coins, start, end, atr_p, mult):
    raw_data = helper.fetch_historical_prices(coins, start, end)
    processed = {}
    for coin, df in raw_data.items():
        processed[coin] = helper.compute_indicators(df, atr_period=atr_p, ut_mult=mult)
    return processed

# Cache backtest simulations for instantaneous tab switching
@st.cache_data
def get_simulations_results(processed, start, cap, fee, slip):
    results = {}
    #dcs
    results["Discount Coin Strategy (DCS)"] = helper.simulate_dcs(processed, start, cap, fee, slip)
    #chess
    results["Chess Trading Strategy"] = helper.simulate_chess(processed, start, cap, fee, slip)
    #hft
    results["HFT Vector Bundle"] = helper.simulate_hft(processed, start, cap, fee, slip)
    #geometry
    results["Market Geometry Strategy"] = helper.simulate_geometry(processed, start, cap, fee, slip)
    #bss
    results["Basket Selection Strategy (BSS)"] = helper.simulate_bss(processed, start, cap, fee, slip)
    #arbitrage
    results["Crypto Arbitrage"] = helper.simulate_arbitrage(processed, start, cap, fee, slip)
    return results

with st.spinner("⚡ Fetching market candles and executing backtests on the fly..."):
    processed_data = get_processed_data(tuple(selected_coins), start_date, end_date, atr_period, ut_mult)
    
    if not processed_data:
        st.error("❌ Failed to download historical data. Please adjust start date or verify internet connection.")
        st.stop()
        
    sim_results = get_simulations_results(processed_data, start_date, starting_capital, fee_pct, slip_pct)

available_strategies = list(helper.strategies.keys())

# Align daily returns
aligned_data = helper.get_aligned_strategy_returns(sim_results)

# ---------------------------------------------------------
# UI TABS
# ---------------------------------------------------------
tabs = st.tabs([
    "📈 Strategy Comparison", 
    "🎯 Dynamic Portfolio Builder", 
    "🔥 Correlation Analysis", 
    "🔍 Trade & Strategy Explorer"
])

# ---------------------------------------------------------
# TAB 1: STRATEGY COMPARISON
# ---------------------------------------------------------
with tabs[0]:
    st.markdown("<div class='section-header'>Strategy Comparison Matrix</div>", unsafe_allow_html=True)
    
    comparison_rows = []
    for name in available_strategies:
        curve, trades = sim_results[name]
        
        metrics = helper.calculate_metrics(curve, starting_capital)
        
        # Trade metrics
        if not trades.empty:
            total_tr = len(trades)
            wins = len(trades[trades["Profit"] > 0])
            win_rate = (wins / total_tr * 100.0)
        else:
            total_tr = 0
            win_rate = 0.0
            
        comparison_rows.append({
            "Strategy": name,
            "CAGR (%)": f"{metrics['CAGR']:.2f}%",
            "Sharpe Ratio": f"{metrics['Sharpe']:.2f}",
            "Max Drawdown": f"{metrics['Max_DD']:.2f}%",
            "Total Return": f"{metrics['Total_Return']:.2f}%",
            "Total Trades": total_tr,
            "Win Rate (%)": f"{win_rate:.2f}%",
            "Ending Capital ($)": f"${metrics['Ending_Capital']:,.2f}"
        })
        
    comparison_df = pd.DataFrame(comparison_rows)
    
    # Identify top performers
    sorted_df = comparison_df.copy()
    sorted_df["CAGR_Num"] = sorted_df["CAGR (%)"].str.replace("%", "").astype(float)
    sorted_df["Sharpe_Num"] = sorted_df["Sharpe Ratio"].astype(float)
    top_cagr = sorted_df.sort_values("CAGR_Num", ascending=False).iloc[0]
    top_sharpe = sorted_df.sort_values("Sharpe_Num", ascending=False).iloc[0]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🔥 Highest CAGR Strategy</div>
            <div class="metric-value">{top_cagr['CAGR (%)']}</div>
            <div class="metric-sub">{top_cagr['Strategy']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🛡️ Best Sharpe Ratio</div>
            <div class="metric-value">Sharpe {top_sharpe['Sharpe Ratio']}</div>
            <div class="metric-sub">{top_sharpe['Strategy']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🪙 Active Coins Basket</div>
            <div class="metric-value">{len(selected_coins)} Assets</div>
            <div class="metric-sub">{', '.join(selected_coins)}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(comparison_df.set_index("Strategy"), use_container_width=True)
    
    st.markdown("<div class='section-header'>Relative Equity Growth Comparison (Base = 1.0)</div>", unsafe_allow_html=True)
    
    # Scale curves to 1.0 base
    scaled_df = pd.DataFrame({"Date": aligned_data["Date"]})
    active_cols = []
    for name in available_strategies:
        eq_col = f"{name}_Equity"
        if eq_col in aligned_data.columns:
            scaled_df[name] = aligned_data[eq_col] / aligned_data[eq_col].iloc[0]
            active_cols.append(name)
            
    fig = px.line(
        scaled_df, 
        x="Date", 
        y=active_cols,
        labels={"value": "Relative Equity", "variable": "Strategy"},
        title="Strategy Equity Growth Comparison"
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Strategies",
        xaxis_gridcolor="rgba(255,255,255,0.05)",
        yaxis_gridcolor="rgba(255,255,255,0.05)",
        font=dict(color="#ffffff")
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: DYNAMIC PORTFOLIO BUILDER
# ---------------------------------------------------------
with tabs[1]:
    st.markdown("<div class='section-header'>Construct Your Combined Portfolio</div>", unsafe_allow_html=True)
    st.markdown("Allocate capital weights across different crypto trading models to simulate a diversified multi-strategy portfolio.")
    
    selected_strats = st.multiselect(
        "Strategies to Include",
        options=available_strategies,
        default=available_strategies[:3]
    )
    
    if not selected_strats:
        st.warning("⚠️ Please select at least one strategy to build a combined portfolio.")
    else:
        st.markdown("#### Allocation Weights")
        weights = []
        w_cols = st.columns(len(selected_strats))
        for idx, (name, col) in enumerate(zip(selected_strats, w_cols)):
            with col:
                w = st.slider(f"{name} (%)", min_value=0, max_value=100, value=100 // len(selected_strats), step=5, key=f"w_c_{name}")
                weights.append(w)
                
        if sum(weights) == 0:
            st.error("❌ Total weight cannot be 0%. Please allocate capital to at least one strategy.")
        else:
            # Standardize weights
            norm_w = [w / sum(weights) for w in weights]
            
            # Simulate combined curve
            portfolio_equity = np.zeros(len(aligned_data))
            portfolio_equity[0] = starting_capital
            
            # Weighted average return calculation
            combined_return = np.zeros(len(aligned_data))
            for name, w_val in zip(selected_strats, norm_w):
                ret_col = f"{name}_Return"
                combined_return += w_val * aligned_data[ret_col].values
                
            for i in range(1, len(aligned_data)):
                portfolio_equity[i] = portfolio_equity[i-1] * (1.0 + combined_return[i])
                
            portfolio_df = pd.DataFrame({
                "Equity": portfolio_equity
            }, index=aligned_data["Date"])
            
            p_metrics = helper.calculate_metrics(portfolio_df, starting_capital)
            
            # Individual components table
            comp_rows = []
            for name, w_val in zip(selected_strats, norm_w):
                curve, _ = sim_results[name]
                m = helper.calculate_metrics(curve, starting_capital)
                comp_rows.append({
                    "Strategy": name,
                    "Weight": f"{w_val*100:.1f}%",
                    "CAGR": f"{m['CAGR']:.2f}%",
                    "Sharpe Ratio": f"{m['Sharpe']:.2f}",
                    "Max Drawdown": f"{m['Max_DD']:.2f}%"
                })
            comp_df = pd.DataFrame(comp_rows)
            
            st.markdown("<div class='section-header'>Simulated Combined Portfolio Metrics</div>", unsafe_allow_html=True)
            
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">📊 Combined Portfolio CAGR</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #10b981, #059669); -webkit-background-clip: text;">{p_metrics['CAGR']:.2f}%</div>
                    <div class="metric-sub">Weighted Annualized Return</div>
                </div>
                """, unsafe_allow_html=True)
            with pc2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🛡️ Portfolio Sharpe Ratio</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #10b981, #059669); -webkit-background-clip: text;">{p_metrics['Sharpe']:.2f}</div>
                    <div class="metric-sub">Risk Adjusted Return Metric</div>
                </div>
                """, unsafe_allow_html=True)
            with pc3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">📉 Portfolio Max Drawdown</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #ef4444, #dc2626); -webkit-background-clip: text;">{p_metrics['Max_DD']:.2f}%</div>
                    <div class="metric-sub">Peak to Valley Fall</div>
                </div>
                """, unsafe_allow_html=True)
            with pc4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">💰 Ending Capital Value</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #10b981, #059669); -webkit-background-clip: text;">${p_metrics['Ending_Capital']:,.2f}</div>
                    <div class="metric-sub">Starting Capital: ${starting_capital:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Portfolio Composition Details")
            st.dataframe(comp_df.set_index("Strategy"), use_container_width=True)
            
            st.markdown("<div class='section-header'>Portfolio Equity Curve (Absolute USD Value)</div>", unsafe_allow_html=True)
            
            fig_p = go.Figure()
            # Portfolio Line
            fig_p.add_trace(go.Scatter(
                x=portfolio_df.index,
                y=portfolio_df["Equity"],
                name="BLENDED PORTFOLIO",
                line=dict(color="#10b981", width=4)
            ))
            
            # Component lines (scaled to starting capital)
            for name, w_val in zip(selected_strats, norm_w):
                eq_col = f"{name}_Equity"
                comp_scaled = (aligned_data[eq_col] / aligned_data[eq_col].iloc[0]) * starting_capital
                fig_p.add_trace(go.Scatter(
                    x=aligned_data["Date"],
                    y=comp_scaled,
                    name=f"{name} ({w_val*100:.0f}%)",
                    line=dict(width=1.5, dash="dot"),
                    opacity=0.6
                ))
                
            fig_p.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis_gridcolor="rgba(255,255,255,0.05)",
                yaxis_gridcolor="rgba(255,255,255,0.05)",
                font=dict(color="#ffffff"),
                xaxis_title="Date",
                yaxis_title="Portfolio Value ($)"
            )
            st.plotly_chart(fig_p, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: CORRELATION ANALYSIS
# ---------------------------------------------------------
with tabs[2]:
    st.markdown("<div class='section-header'>Strategy Daily Returns Correlation Matrix</div>", unsafe_allow_html=True)
    st.markdown("A diversified multi-strategy desk exploits low correlations between systems. Analyze Pearson correlation coefficients of daily returns.")
    
    corr_strats = st.multiselect(
        "Select Strategies for Correlation Matrix",
        options=available_strategies,
        default=available_strategies
    )
    
    if len(corr_strats) < 2:
        st.warning("⚠️ Please select at least two strategies to calculate correlations.")
    else:
        # Build returns matrix
        ret_cols = [f"{name}_Return" for name in corr_strats]
        returns_df = aligned_data[ret_cols].copy()
        returns_df.columns = corr_strats
        
        corr_matrix = returns_df.corr()
        
        fig_h = px.imshow(
            corr_matrix,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="Purples",
            labels=dict(color="Correlation"),
            title="Correlation Heatmap (Daily Returns)"
        )
        fig_h.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff")
        )
        st.plotly_chart(fig_h, use_container_width=True)
        
        # Suggest lowest correlation pair
        st.markdown("##### 💡 Key Diversification Insights")
        c_vals = corr_matrix.copy()
        for col in c_vals.columns:
            c_vals.loc[col, col] = np.nan
        flat_c = c_vals.unstack().dropna()
        sorted_c = flat_c.sort_values()
        
        if not sorted_c.empty:
            low_pair = sorted_c.index[0]
            low_val = sorted_c.iloc[0]
            st.info(f"👉 **Best Diversification Pair**: **{low_pair[0]}** and **{low_pair[1]}** have the lowest correlation of **{low_val:.2f}**. Combining these two models creates a smoother equity curve by offsetting individual system drawdowns.")

# ---------------------------------------------------------
# TAB 4: TRADE & STRATEGY EXPLORER
# ---------------------------------------------------------
with tabs[3]:
    st.markdown("<div class='section-header'>Strategy Deep-Dive & Historical Trades</div>", unsafe_allow_html=True)
    
    selected_explore = st.selectbox(
        "Select Strategy to Explore",
        options=available_strategies
    )
    
    st.markdown(f"**Description**: {helper.strategies[selected_explore]['desc']}")
    
    _, trades = sim_results[selected_explore]
    
    if trades.empty:
        st.info("No trades executed by this strategy in the selected timeframe.")
    else:
        # Calculate statistics
        total_tr = len(trades)
        winning_tr = trades[trades["Profit"] > 0]
        losing_tr = trades[trades["Profit"] <= 0]
        
        win_c = len(winning_tr)
        loss_c = len(losing_tr)
        win_r = (win_c / total_tr) * 100.0 if total_tr > 0 else 0.0
        
        avg_w = winning_tr["Profit"].mean() if win_c > 0 else 0.0
        avg_l = losing_tr["Profit"].mean() if loss_c > 0 else 0.0
        rr_ratio = abs(avg_w / avg_l) if avg_l != 0 else np.nan
        
        best_tr = trades["Profit"].max()
        worst_tr = trades["Profit"].min()
        
        # UI Metrics
        ec1, ec2, ec3, ec4 = st.columns(4)
        with ec1:
            st.metric("Total Completed Trades", f"{total_tr}")
        with ec2:
            st.metric("Win Rate (%)", f"{win_r:.2f}%", f"{win_c} Wins / {loss_c} Losses")
        with ec3:
            st.metric("Avg Win / Avg Loss ($)", f"${avg_w:,.2f} / ${avg_l:,.2f}", f"R:R Ratio: {rr_ratio:.2f}")
        with ec4:
            st.metric("Best / Worst Trade ($)", f"${best_tr:,.2f}", f"Worst: ${worst_tr:,.2f}")
            
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.markdown("##### Exit Reason Analysis")
            if "Exit Reason" in trades.columns:
                reasons = trades["Exit Reason"].value_counts().reset_index()
                reasons.columns = ["Exit Reason", "Count"]
                fig_pie = px.pie(reasons, values="Count", names="Exit Reason", hole=0.4, title="Trade Exit Reasons")
                fig_pie.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#ffffff")
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.caption("No exit reason details logged.")
                
        with col_r:
            st.markdown("##### Realized Profit Distribution")
            fig_hist = px.histogram(
                trades,
                x="Profit",
                nbins=30,
                title="Profit/Loss Distribution ($)",
                color_discrete_sequence=["#8b5cf6"]
            )
            fig_hist.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ffffff")
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        st.markdown("##### 📄 Complete Trade Ledger")
        
        # Display formatted trade ledger
        display_df = trades.copy()
        for c in display_df.columns:
            if "Date" in str(c) or "Timestamp" in str(c):
                display_df[c] = pd.to_datetime(display_df[c]).dt.strftime("%Y-%m-%d")
                
        st.dataframe(display_df, use_container_width=True)
