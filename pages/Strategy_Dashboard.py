# pages/Strategy_Dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys

# Ensure UTF-8 and import StrategyHelper
from strategy_helper import StrategyHelper

st.set_page_config(
    page_title="Multi-Strategy Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling (HSL and Glassmorphism details)
st.markdown("""
<style>
    /* Premium CSS styling */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.07);
    }
    .metric-title {
        color: rgba(255, 255, 255, 0.7);
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #00B4DB, #0083B0);
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
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Title & Description
st.title("📊 Institutional Multi-Strategy Portfolio Dashboard")
st.markdown("Analyze individual strategy performance, run dynamic weighted portfolio backtests, check correlation heatmaps, and explore historical trades.")

# Initialize strategy helper
@st.cache_resource
def get_strategy_helper_instance():
    return StrategyHelper()

helper = get_strategy_helper_instance()
available_strategies = list(helper.strategies.keys())

# Sidebar Controls
st.sidebar.header("🕹️ Dashboard Controls")
horizon_option = st.sidebar.selectbox(
    "Select Analysis Timeframe",
    options=["10-Year (Full Backtest)", "5-Year", "1-Year"],
    index=0
)

# Convert selected timeframe to cutoff date
# Note: Backtests mostly end around mid-2026 (approx 2026-05-26)
latest_date = pd.to_datetime("2026-05-26")
if horizon_option == "1-Year":
    start_cutoff = latest_date - timedelta(days=365)
elif horizon_option == "5-Year":
    start_cutoff = latest_date - timedelta(days=1825)
else:
    start_cutoff = pd.to_datetime("2016-06-02") # start of backtest universe

st.sidebar.info(f"Analyzing trades and equity curves from **{start_cutoff.strftime('%Y-%m-%d')}** to **{latest_date.strftime('%Y-%m-%d')}**.")

# Pre-load aligned daily returns to establish active strategy list
@st.cache_data
def get_strategy_aligned_returns_cached(strategies_list):
    return helper.get_aligned_strategy_returns(strategies_list)

aligned_data = get_strategy_aligned_returns_cached(available_strategies)

if aligned_data is None or aligned_data.empty:
    import os
    st.error("❌ Error loading strategy backtest files. Please verify the files are present in the workspace.")
    st.markdown("### 🔍 Diagnostic Debug Info (Streamlit Cloud)")
    st.write("Current Directory:", os.getcwd())
    try:
        st.write("Files in Root:", sorted([f for f in os.listdir('.') if f.endswith('.xlsx') or f.endswith('.py') or f.endswith('.csv')]))
    except Exception as ex:
        st.write("Error listing root:", ex)
    st.write("Helper workspace_dir:", helper.workspace_dir)
    try:
        if os.path.exists(helper.workspace_dir):
            st.write("Files in workspace_dir:", sorted([f for f in os.listdir(helper.workspace_dir) if f.endswith('.xlsx')]))
        else:
            st.write("workspace_dir does not exist:", helper.workspace_dir)
    except Exception as ex:
        st.write("Error listing workspace_dir:", ex)
    st.stop()

# Filter by selected date range
filtered_aligned = aligned_data[
    (aligned_data["Date"] >= start_cutoff) & (aligned_data["Date"] <= latest_date)
].reset_index(drop=True)

# Main Application Tabs
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
    
    # Calculate performance metrics for all strategies in timeframe
    comparison_rows = []
    for name in available_strategies:
        eq_col = f"{name}_Equity"
        if eq_col in filtered_aligned.columns:
            strat_equity = filtered_aligned[["Date", eq_col]].copy()
            strat_equity.columns = ["Date", "Equity"]
            # Normalize equity starting point to initial_capital for visual comparison
            initial_cap = helper.strategies[name]["initial_capital"]
            metrics = helper.calculate_metrics(strat_equity, initial_capital=initial_cap)
            
            # Count trades
            trades = helper.load_strategy_trades(name)
            if not trades.empty:
                filtered_trades = trades[
                    (trades["Exit Date"] >= start_cutoff) & (trades["Exit Date"] <= latest_date)
                ]
                trade_count = len(filtered_trades)
                win_count = len(filtered_trades[filtered_trades["Profit"] > 0])
                win_rate = (win_count / trade_count * 100.0) if trade_count > 0 else 0.0
            else:
                trade_count = 0
                win_rate = 0.0
                
            comparison_rows.append({
                "Strategy": name,
                "CAGR (%)": f"{metrics['CAGR']:.2f}%",
                "Sharpe Ratio": f"{metrics['Sharpe']:.2f}",
                "Max Drawdown": f"{metrics['Max_DD']:.2f}%",
                "Total Return": f"{metrics['Total_Return']:.2f}%",
                "Total Trades": trade_count,
                "Win Rate (%)": f"{win_rate:.2f}%",
                "Ending Capital (INR)": f"₹{metrics['Ending_Capital']:,.2f}"
            })
            
    comparison_df = pd.DataFrame(comparison_rows)
    
    # Render premium metrics side by side for top performing strategy
    sorted_df = comparison_df.copy()
    sorted_df["CAGR_Num"] = sorted_df["CAGR (%)"].str.replace("%", "").astype(float)
    sorted_df["Sharpe_Num"] = sorted_df["Sharpe Ratio"].astype(float)
    top_cagr_row = sorted_df.sort_values("CAGR_Num", ascending=False).iloc[0]
    top_sharpe_row = sorted_df.sort_values("Sharpe_Num", ascending=False).iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🔥 Highest CAGR Strategy</div>
            <div class="metric-value">{top_cagr_row['CAGR (%)']}</div>
            <div class="metric-sub">{top_cagr_row['Strategy']} ({horizon_option})</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🛡️ Best Risk-Adjusted Return</div>
            <div class="metric-value">Sharpe {top_sharpe_row['Sharpe Ratio']}</div>
            <div class="metric-sub">{top_sharpe_row['Strategy']} ({horizon_option})</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🧺 Total Strategies Available</div>
            <div class="metric-value">{len(available_strategies)}</div>
            <div class="metric-sub">Multi-Asset & Arbitrage Models Included</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(comparison_df.set_index("Strategy"), use_container_width=True)
    
    st.markdown("<div class='section-header'>Relative Equity Growth Comparison (Base = 1.0)</div>", unsafe_allow_html=True)
    st.caption("All strategies are scaled to start at 1.0 to easily compare relative performance over the selected timeframe.")
    
    # Scale all curves to 1.0
    scaled_df = pd.DataFrame({"Date": filtered_aligned["Date"]})
    for name in available_strategies:
        eq_col = f"{name}_Equity"
        if eq_col in filtered_aligned.columns:
            scaled_df[name] = filtered_aligned[eq_col] / filtered_aligned[eq_col].iloc[0]
            
    fig = px.line(scaled_df, x="Date", y=available_strategies, 
                  labels={"value": "Relative Equity", "variable": "Strategy"},
                  title=f"Equity Growth Comparison ({horizon_option} Horizon)")
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
    st.markdown("Choose multiple strategies, allocate capital weights, and backtest your customized combined portfolio dynamically.")
    
    selected_strats = st.multiselect(
        "Select strategies to include in portfolio:",
        options=available_strategies,
        default=["Discount Stock Strategy v2 (DSS2)", "Chess Trading Strategy", "Vector HFT"]
    )
    
    if not selected_strats:
        st.warning("⚠️ Please select at least one strategy to run the simulation.")
    else:
        # Generate sliders for weights
        st.markdown("#### Capital Allocation Weights")
        weights = []
        cols = st.columns(len(selected_strats))
        for idx, (name, col) in enumerate(zip(selected_strats, cols)):
            with col:
                weight = st.slider(f"{name} (%)", min_value=0, max_value=100, value=100 // len(selected_strats), step=5, key=f"w_{name}")
                weights.append(weight)
                
        if sum(weights) == 0:
            st.error("❌ The sum of weights cannot be 0. Please allocate capital to at least one strategy.")
        else:
            # Simulate combined portfolio
            portfolio_cap = st.number_input("Starting Capital (INR)", min_value=10000, value=100000, step=10000)
            
            # Standardize weights
            norm_w = [w / sum(weights) for w in weights]
            
            # Fetch aligned returns filtered by cutoff
            p_returns = filtered_aligned[["Date"]].copy()
            
            # Reconstruct daily combined return
            combined_ret = np.zeros(len(filtered_aligned))
            for name, w in zip(selected_strats, norm_w):
                ret_col = f"{name}_Return"
                combined_ret += w * filtered_aligned[ret_col].values
                
            # Construct portfolio equity curve
            portfolio_equity = np.zeros(len(filtered_aligned))
            portfolio_equity[0] = portfolio_cap
            for i in range(1, len(filtered_aligned)):
                portfolio_equity[i] = portfolio_equity[i-1] * (1.0 + combined_ret[i])
                
            portfolio_df = pd.DataFrame({
                "Date": filtered_aligned["Date"],
                "Equity": portfolio_equity,
                "Daily_Return": combined_ret
            })
            
            # Compute portfolio metrics
            p_metrics = helper.calculate_metrics(portfolio_df, initial_capital=portfolio_cap)
            
            # Calculate metrics for individual components inside timeframe for comparison
            comp_metrics = []
            for name, w in zip(selected_strats, norm_w):
                eq_col = f"{name}_Equity"
                comp_eq = filtered_aligned[["Date", eq_col]].copy()
                comp_eq.columns = ["Date", "Equity"]
                m = helper.calculate_metrics(comp_eq, initial_capital=portfolio_cap)
                comp_metrics.append({
                    "Strategy": name,
                    "Weight": f"{w*100:.1f}%",
                    "CAGR": f"{m['CAGR']:.2f}%",
                    "Sharpe Ratio": f"{m['Sharpe']:.2f}",
                    "Max Drawdown": f"{m['Max_DD']:.2f}%",
                    "Total Return": f"{m['Total_Return']:.2f}%"
                })
            comp_df = pd.DataFrame(comp_metrics)
            
            # Render Portfolio vs Components side by side
            st.markdown("<div class='section-header'>Simulated Combined Portfolio Metrics</div>", unsafe_allow_html=True)
            
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">📊 Combined Portfolio CAGR</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #11998e, #38ef7d); -webkit-background-clip: text;">{p_metrics['CAGR']:.2f}%</div>
                    <div class="metric-sub">Weighted Annualized Return</div>
                </div>
                """, unsafe_allow_html=True)
            with pc2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🛡️ Portfolio Sharpe Ratio</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #11998e, #38ef7d); -webkit-background-clip: text;">{p_metrics['Sharpe']:.2f}</div>
                    <div class="metric-sub">Diversified Risk Adjuster</div>
                </div>
                """, unsafe_allow_html=True)
            with pc3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">📉 Portfolio Max Drawdown</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #ff416c, #ff4b2b); -webkit-background-clip: text;">{p_metrics['Max_DD']:.2f}%</div>
                    <div class="metric-sub">Peak-to-Trough Drawdown</div>
                </div>
                """, unsafe_allow_html=True)
            with pc4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">💰 Ending Capital Value</div>
                    <div class="metric-value" style="background: linear-gradient(135deg, #11998e, #38ef7d); -webkit-background-clip: text;">₹{p_metrics['Ending_Capital']:,.2f}</div>
                    <div class="metric-sub">Initial Capital: ₹{portfolio_cap:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Portfolio Composition Details")
            st.dataframe(comp_df.set_index("Strategy"), use_container_width=True)
            
            # Plot Combined Equity curve vs Components
            st.markdown("<div class='section-header'>Portfolio Equity Curve (Absolute INR Value)</div>", unsafe_allow_html=True)
            
            fig_p = go.Figure()
            # Add Combined Portfolio Line
            fig_p.add_trace(go.Scatter(
                x=portfolio_df["Date"], 
                y=portfolio_df["Equity"], 
                name="COMBINED PORTFOLIO",
                line=dict(color="#38ef7d", width=4, dash="solid")
            ))
            
            # Add Individual Strategy scaled lines for absolute capital reference
            for name, w in zip(selected_strats, norm_w):
                eq_col = f"{name}_Equity"
                comp_scaled_cap = (filtered_aligned[eq_col] / filtered_aligned[eq_col].iloc[0]) * portfolio_cap
                fig_p.add_trace(go.Scatter(
                    x=filtered_aligned["Date"],
                    y=comp_scaled_cap,
                    name=f"{name} ({w*100:.0f}%)",
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
                yaxis_title="Portfolio Value (INR)"
            )
            st.plotly_chart(fig_p, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: CORRELATION ANALYSIS
# ---------------------------------------------------------
with tabs[2]:
    st.markdown("<div class='section-header'>Strategy Daily Returns Correlation Matrix</div>", unsafe_allow_html=True)
    st.markdown("Building a diversified portfolio requires combining **uncorrelated** strategies. Check which strategies have low correlation to maximize diversification benefits.")
    
    # Select strategies for correlation analysis
    corr_strats = st.multiselect(
        "Select strategies for correlation heatmap:",
        options=available_strategies,
        default=available_strategies
    )
    
    if len(corr_strats) < 2:
        st.warning("⚠️ Please select at least two strategies to compute correlations.")
    else:
        # Build returns df
        ret_cols = [f"{name}_Return" for name in corr_strats]
        returns_df = filtered_aligned[ret_cols].copy()
        returns_df.columns = corr_strats
        
        # Calculate correlation matrix
        corr_matrix = returns_df.corr()
        
        # Plot using Plotly Heatmap
        fig_h = px.imshow(
            corr_matrix,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            labels=dict(color="Correlation Coefficient"),
            title=f"Correlation Heatmap ({horizon_option} Horizon)"
        )
        
        fig_h.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff")
        )
        st.plotly_chart(fig_h, use_container_width=True)
        
        # Suggest low correlation pairs
        st.markdown("##### 💡 Key Diversification Insights")
        # Find lowest correlation pair (ignoring diagonals)
        corr_vals = corr_matrix.copy()
        np.fill_diagonal(corr_vals.values, np.nan)
        flat_corr = corr_vals.unstack().dropna()
        sorted_corr = flat_corr.sort_values()
        
        lowest_pair = sorted_corr.index[0]
        lowest_val = sorted_corr.iloc[0]
        
        st.info(f"👉 **Best Diversification Pair**: **{lowest_pair[0]}** and **{lowest_pair[1]}** have the lowest correlation of **{lowest_val:.2f}**. Combining them will significantly smooth out equity curves and reduce drawdowns.")

# ---------------------------------------------------------
# TAB 4: TRADE & STRATEGY EXPLORER
# ---------------------------------------------------------
with tabs[3]:
    st.markdown("<div class='section-header'>Strategy Deep-Dive & Historical Trades</div>", unsafe_allow_html=True)
    
    selected_explore_strat = st.selectbox(
        "Select a strategy to explore:",
        options=available_strategies
    )
    
    cfg = helper.strategies[selected_explore_strat]
    st.markdown(f"**Description**: {cfg['desc']}")
    
    # Load trade ledger
    with st.spinner("Loading strategy trade log..."):
        trades = helper.load_strategy_trades(selected_explore_strat)
        
    if trades.empty:
        st.info("No detailed trade logs found for this strategy, or file is empty.")
    else:
        # Filter trades by selected timeframe
        filtered_trades = trades[
            (trades["Exit Date"] >= start_cutoff) & (trades["Exit Date"] <= latest_date)
        ].reset_index(drop=True)
        
        if filtered_trades.empty:
            st.warning("No trades found in the selected timeframe.")
        else:
            # Stats calculation
            total_trades = len(filtered_trades)
            winning_trades = filtered_trades[filtered_trades["Profit"] > 0]
            losing_trades = filtered_trades[filtered_trades["Profit"] <= 0]
            
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = (win_count / total_trades) * 100.0 if total_trades > 0 else 0.0
            
            avg_win = winning_trades["Profit"].mean() if win_count > 0 else 0.0
            avg_loss = losing_trades["Profit"].mean() if loss_count > 0 else 0.0
            profit_factor = (winning_trades["Profit"].sum() / abs(losing_trades["Profit"].sum())) if loss_count > 0 and losing_trades["Profit"].sum() != 0 else np.nan
            
            best_trade = filtered_trades["Profit"].max()
            worst_trade = filtered_trades["Profit"].min()
            
            # Metric UI
            ec1, ec2, ec3, ec4 = st.columns(4)
            with ec1:
                st.metric("Total Trades Exited", f"{total_trades}", help="Total number of trades completed in selected timeframe")
            with ec2:
                st.metric("Win Rate", f"{win_rate:.2f}%", f"{win_count} Wins / {loss_count} Losses")
            with ec3:
                st.metric("Avg Win / Avg Loss", f"₹{avg_win:,.2f} / ₹{avg_loss:,.2f}", f"Risk-Reward Ratio: {abs(avg_win/avg_loss) if avg_loss != 0 else np.nan:.2f}")
            with ec4:
                st.metric("Best / Worst Trade", f"₹{best_trade:,.2f}", f"Worst: ₹{worst_trade:,.2f}")
                
            col_l, col_r = st.columns([1, 1])
            with col_l:
                st.markdown("##### Exit Reason Analysis")
                if "Exit Reason" in filtered_trades.columns:
                    reason_counts = filtered_trades["Exit Reason"].value_counts().reset_index()
                    reason_counts.columns = ["Exit Reason", "Count"]
                    fig_pie = px.pie(reason_counts, values="Count", names="Exit Reason", hole=0.4, title="Trade Exit Reasons")
                    fig_pie.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#ffffff")
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.caption("No exit reason data available.")
                    
            with col_r:
                st.markdown("##### Profit Distribution")
                fig_hist = px.histogram(filtered_trades, x="Profit", nbins=50, title="Realized Profit Distribution (INR)", color_discrete_sequence=["#00B4DB"])
                fig_hist.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#ffffff")
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
            st.markdown("##### 📄 Complete Trade Ledger")
            # Format dataframe dates for visual elegance
            display_df = filtered_trades.copy()
            # Ensure Date columns are string formatted
            for c in display_df.columns:
                if "Date" in str(c) or "Timestamp" in str(c):
                    display_df[c] = display_df[c].dt.strftime('%Y-%m-%d')
            
            st.dataframe(display_df, use_container_width=True)
