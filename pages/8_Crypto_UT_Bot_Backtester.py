# pages/8_Crypto_UT_Bot_Backtester.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="Crypto UTBot Backtesting Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Obsidian & Glowing Crimson Premium Styling
st.markdown("""
<style>
    .reportview-container {
        background-color: #0b0e11;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(248, 90, 90, 0.4);
    }
    .status-buy {
        background-color: rgba(46, 204, 113, 0.15);
        border: 1px solid rgb(46, 204, 113);
        border-radius: 8px;
        padding: 8px;
        color: #2ecc71;
        font-weight: 700;
        text-align: center;
    }
    .status-sell {
        background-color: rgba(248, 90, 90, 0.15);
        border: 1px solid rgb(248, 90, 90);
        border-radius: 8px;
        padding: 8px;
        color: #f85a5a;
        font-weight: 700;
        text-align: center;
    }
    .alert-header {
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("♛ Crypto UTBot Backtesting Dashboard")
st.markdown("Run high-fidelity historical simulations of the Average True Range (ATR) trailing-stop trend strategy across multiple major cryptocurrencies.")

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("⚙️ UTBot Strategy Parameters")

selected_coins = st.sidebar.multiselect(
    "Select Cryptocurrencies",
    ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "DOT", "LINK", "LTC", "AVAX"],
    default=["BTC", "ETH", "SOL"],
    help="Select one or multiple coins to backtest and analyze."
)

col_sdate, col_edate = st.sidebar.columns(2)
with col_sdate:
    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=365))
with col_edate:
    end_date = st.date_input("End Date", datetime.now())

starting_capital = st.sidebar.number_input("Starting Capital ($)", min_value=100.0, value=10000.0, step=500.0)
inr_rate = st.sidebar.number_input("USD/INR Rate (₹)", min_value=1.0, value=83.50, step=0.10)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Strategy Tuning")

atr_period = st.sidebar.slider("ATR Period", min_value=1, max_value=30, value=10, help="Window size to compute True Range volatility.")
multiplier = st.sidebar.slider("ATR Multiplier", min_value=0.5, max_value=5.0, value=1.0, step=0.1, help="Stop loss distance multiplier.")

fee_pct = st.sidebar.number_input("Transaction Fee (%)", min_value=0.0, max_value=2.0, value=0.10, step=0.05) / 100.0
slip_pct = st.sidebar.number_input("Slippage Drag (%)", min_value=0.0, max_value=2.0, value=0.10, step=0.05) / 100.0

# ---------------------------------------------------------
# CORE CALCULATIONS: UT BOT ALERTS ENGINE
# ---------------------------------------------------------
def compute_utbot(df, atr_p=10, mult=1.0):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    
    tr = np.maximum(high_low, np.maximum(high_close, low_close))
    atr = tr.rolling(atr_p).mean()
    
    df["tr"] = tr
    df["atr"] = atr
    
    # Trailing Stop Bands
    df["upper"] = df["Close"] - mult * df["atr"]
    df["lower"] = df["Close"] + mult * df["atr"]
    
    trend = []
    curr_trend = 1
    
    for i in range(len(df)):
        if i == 0:
            trend.append(curr_trend)
            continue
            
        close_val = df["Close"].iloc[i]
        prev_lower = df["lower"].iloc[i-1]
        prev_upper = df["upper"].iloc[i-1]
        
        # Guard against NaN upper/lower stop bands during initialization period
        if pd.isna(prev_lower) or pd.isna(prev_upper):
            trend.append(curr_trend)
            continue
            
        if close_val > prev_lower:
            curr_trend = 1
        elif close_val < prev_upper:
            curr_trend = -1
            
        trend.append(curr_trend)
        
    df["trend"] = trend
    df["buy"] = (df["trend"] == 1) & (df["trend"].shift() == -1)
    df["sell"] = (df["trend"] == -1) & (df["trend"].shift() == 1)
    
    return df

@st.cache_data(ttl=3600)
def fetch_historical_prices(coin, start, end):
    ticker = f"{coin}-USD"
    # Fetch wider start window to compute ATR cleanly prior to backtest range
    buffer_start = start - timedelta(days=45)
    df = yf.download(ticker, start=buffer_start, end=end)
    if df.empty:
        return pd.DataFrame()
    
    # Flatten MultiIndex columns if present (common in newer yfinance versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    return df

# ---------------------------------------------------------
# BACKTESTER LOGIC
# ---------------------------------------------------------
def run_utbot_backtest(df, start_dt, cap, fee, slip):
    # Filter backtest range
    backtest_df = df.loc[df.index >= pd.to_datetime(start_dt)].copy()
    if len(backtest_df) < 2:
        return pd.Series(), [], 0.0, 0
        
    cash = cap
    position = 0.0
    status = "CASH"
    
    equity_curve = []
    trades = []
    
    entry_price = 0.0
    entry_date = None
    
    for current_date, row in backtest_df.iterrows():
        close_price = float(row["Close"])
        
        # 1. Check exit/sell signal
        if status == "IN_POSITION" and row["sell"]:
            cash = position * close_price * (1.0 - fee - slip)
            pnl_raw = cash - pos_entry_capital
            pnl_pct = (pnl_raw / pos_entry_capital) * 100.0
            
            trades.append({
                "Asset": coin,
                "Type": "Short Exit",
                "Entry Date": entry_date.strftime("%Y-%m-%d"),
                "Exit Date": current_date.strftime("%Y-%m-%d"),
                "Entry Price": entry_price,
                "Exit Price": close_price,
                "Profit ($)": pnl_raw,
                "Profit (%)": pnl_pct
            })
            
            position = 0.0
            status = "CASH"
            
        # 2. Check entry/buy signal
        elif status == "CASH" and row["buy"]:
            pos_entry_capital = cash
            position = cash * (1.0 - fee - slip) / close_price
            cash = 0.0
            status = "IN_POSITION"
            entry_price = close_price
            entry_date = current_date
            
        # 3. Record daily equity
        if status == "IN_POSITION":
            daily_equity = position * close_price
        else:
            daily_equity = cash
            
        equity_curve.append({
            "Date": current_date,
            "Equity": daily_equity
        })
        
    equity_series = pd.DataFrame(equity_curve).set_index("Date")["Equity"]
    
    # Mark to market final day's trade if still open
    if status == "IN_POSITION":
        final_close = float(backtest_df["Close"].iloc[-1])
        final_cash = position * final_close * (1.0 - fee - slip)
        final_pnl = final_cash - pos_entry_capital
        final_pct = (final_pnl / pos_entry_capital) * 100.0
        
        trades.append({
            "Asset": coin,
            "Type": "Open MTM",
            "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Exit Date": backtest_df.index[-1].strftime("%Y-%m-%d"),
            "Entry Price": entry_price,
            "Exit Price": final_close,
            "Profit ($)": final_pnl,
            "Profit (%)": final_pct
        })
        
    return equity_series, trades

# ---------------------------------------------------------
# EXECUTE SIMULATION PORTFOLIO
# ---------------------------------------------------------
if not selected_coins:
    st.info("👈 Please select one or multiple coins in the sidebar to begin.")
else:
    # Gather data & run backtests
    all_prices = {}
    all_equities = {}
    all_benchmarks = {}
    all_trades = []
    comparison_metrics = []
    
    with st.spinner("Harvesting historical candles and executing UTBot alerts simulation..."):
        for coin in selected_coins:
            df = fetch_historical_prices(coin, start_date, end_date)
            if df.empty:
                continue
                
            df = compute_utbot(df, atr_period, multiplier)
            all_prices[coin] = df
            
            # Run backtest
            equity_curve, trades = run_utbot_backtest(df, start_date, starting_capital, fee_pct, slip_pct)
            if equity_curve.empty:
                continue
                
            all_equities[coin] = equity_curve
            all_trades.extend(trades)
            
            # Benchmark Buy & Hold
            start_price = float(df.loc[df.index >= pd.to_datetime(start_date)]["Close"].iloc[0])
            benchmark_curve = df.loc[df.index >= pd.to_datetime(start_date)]["Close"] / start_price * starting_capital * (1.0 - fee_pct - slip_pct)
            all_benchmarks[coin] = benchmark_curve
            
            # Metrics calculations
            end_bal = float(equity_curve.iloc[-1])
            net_ret = (end_bal / starting_capital - 1) * 100.0
            
            # Sharpe
            daily_rets = equity_curve.pct_change().dropna()
            sharpe = np.sqrt(365) * (daily_rets.mean() / daily_rets.std()) if len(daily_rets) > 1 and daily_rets.std() != 0 else 0.0
            
            # Max Drawdown
            peak = equity_curve.cummax()
            dd = (equity_curve - peak) / peak * 100.0
            max_dd = dd.min()
            
            # Win Rate
            profitable_trades = [t for t in trades if t["Profit ($)"] > 0]
            win_rate = (len(profitable_trades) / len(trades) * 100.0) if trades else 0.0
            
            # Profit Factor
            gross_profits = sum(t["Profit ($)"] for t in trades if t["Profit ($)"] > 0)
            gross_losses = abs(sum(t["Profit ($)"] for t in trades if t["Profit ($)"] < 0))
            profit_factor = (gross_profits / gross_losses) if gross_losses != 0 else (gross_profits if gross_profits > 0 else 1.0)
            
            # CAGR
            years = (end_date - start_date).days / 365.0
            cagr = ((end_bal / starting_capital) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0
            
            comparison_metrics.append({
                "Asset": coin,
                "Ending Balance ($)": f"${end_bal:,.2f}",
                "Ending Balance (₹)": f"₹{end_bal * inr_rate:,.2f}",
                "CAGR (%)": f"{cagr:+.2f}%",
                "Total Return (%)": f"{net_ret:+.2f}%",
                "Sharpe Ratio": f"{sharpe:.2f}",
                "Max Drawdown (%)": f"{max_dd:.2f}%",
                "Win Rate (%)": f"{win_rate:.1f}%",
                "Profit Factor": f"{profit_factor:.2f}",
                "Total Trades": len(trades)
            })

    if not all_equities:
        st.error("No historical data could be retrieved for the selected coins and dates. Please try standard assets or expand date range.")
    else:
        # Create Tabs for layout
        tab_backtest, tab_metrics, tab_analytics, tab_alerts = st.tabs([
            "📈 Capital Movement & Backtests",
            "📊 Comparative Metrics Matrix",
            "🧮 Statistical Risk Analytics",
            "🚨 Monospace Alerts Board"
        ])
        
        # =========================================================
        # TAB 1: CAPITAL MOVEMENT & BACKTESTS
        # =========================================================
        with tab_backtest:
            st.subheader("📈 Capital Movement Over Time")
            
            # Select coin to view details
            selected_view_coin = st.selectbox("Select Asset to Highlight", list(all_equities.keys()))
            
            fig = go.Figure()
            # Add strategy equity
            fig.add_trace(go.Scatter(
                x=all_equities[selected_view_coin].index,
                y=all_equities[selected_view_coin].values,
                name="UTBot Alerts Strategy",
                line=dict(color="#f85a5a", width=2.5)
            ))
            # Add Buy-and-Hold benchmark
            fig.add_trace(go.Scatter(
                x=all_benchmarks[selected_view_coin].index,
                y=all_benchmarks[selected_view_coin].values,
                name="Buy & Hold Benchmark",
                line=dict(color="#64748b", width=1.5, dash="dash")
            ))
            
            fig.update_layout(
                title=f"Capital Movement: {selected_view_coin} ($ {starting_capital:,.0f} Initial Allocation)",
                xaxis_title="Date",
                yaxis_title="Equity Value ($)",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)")
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Metrics Highlights
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            coin_metric = next(m for m in comparison_metrics if m["Asset"] == selected_view_coin)
            
            with col_met1:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Final Value ($)</div>
                    <div style="font-size: 20px; font-weight: 700; color: #f8fafc; margin-top: 6px;">{coin_metric['Ending Balance ($)']}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Initial: ${starting_capital:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_met2:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Final Value (₹)</div>
                    <div style="font-size: 20px; font-weight: 700; color: #a29bfe; margin-top: 6px;">{coin_metric['Ending Balance (₹)']}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">USD/INR: ₹{inr_rate:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_met3:
                ret_pct_val = float(coin_metric['Total Return (%)'].replace('%',''))
                ret_color = "#00c896" if ret_pct_val >= 0 else "#f85a5a"
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Total Return (%)</div>
                    <div style="font-size: 20px; font-weight: 700; color: {ret_color}; margin-top: 6px;">{coin_metric['Total Return (%)']}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">CAGR: {coin_metric['CAGR (%)']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_met4:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Max Drawdown (%)</div>
                    <div style="font-size: 20px; font-weight: 700; color: #f85a5a; margin-top: 6px;">{coin_metric['Max Drawdown (%)']}</div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 4px;">Sharpe Ratio: {coin_metric['Sharpe Ratio']}</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Completed trades list for highlighted coin
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📑 Completed Trades Log")
            coin_trades = [t for t in all_trades if t["Asset"] == selected_view_coin]
            
            if not coin_trades:
                st.info(f"No trades completed for {selected_view_coin} inside the selected backtest range. (Buy-and-Hold trend stayed active).")
            else:
                trades_df = pd.DataFrame(coin_trades)
                # Style tables with green/red PnL rows
                styled_df = trades_df.copy()
                styled_df["Profit ($)"] = styled_df["Profit ($)"].map(lambda x: f"${x:+.2f}")
                styled_df["Profit (%)"] = styled_df["Profit (%)"].map(lambda x: f"{x:+.2f}%")
                st.dataframe(styled_df.set_index("Entry Date"), use_container_width=True)

        # =========================================================
        # TAB 2: COMPARATIVE METRICS MATRIX
        # =========================================================
        with tab_metrics:
            st.subheader("📊 Multi-Asset Comparative Metrics Matrix")
            st.markdown("Performance comparison of the UTBot strategy across all selected cryptocurrency portfolios.")
            
            metrics_df = pd.DataFrame(comparison_metrics)
            st.dataframe(metrics_df.set_index("Asset"), use_container_width=True)
            st.caption("Performance matrix. All CAGR and Total Returns are net of configured opening fees and slippage drag. Sharpe ratios are fully annualized based on standard crypto 365-day cycles.")

        # =========================================================
        # TAB 3: STATISTICAL RISK ANALYTICS
        # =========================================================
        with tab_analytics:
            st.subheader("🧮 Statistical Risk Analytics Desk")
            
            # Align daily returns for heatmap and distributions
            returns_df = pd.DataFrame()
            for coin, eq in all_equities.items():
                returns_df[coin] = eq.pct_change().dropna()
                
            col_heat, col_dist = st.columns([1, 1])
            
            with col_heat:
                st.subheader("💜 Strategy Returns Correlation Matrix")
                if returns_df.empty or len(returns_df.columns) < 2:
                    st.info("Correlation analysis requires at least two selected assets.")
                else:
                    corr = returns_df.corr()
                    fig_heat = px.imshow(
                        corr,
                        text_auto=".2f",
                        color_continuous_scale="Purples",
                        labels=dict(color="Correlation")
                    )
                    fig_heat.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0")
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
                    st.caption("Heatmap showing the Pearson correlation matrix of daily equity returns. Lower correlation coefficients indicate higher diversification benefits for portfolio-weighted setups.")
                    
            with col_dist:
                st.subheader("📊 Distribution of Daily Returns")
                if returns_df.empty:
                    st.info("No returns data available to compile distributions.")
                else:
                    # Melt returns_df for easy plotting
                    melted_returns = returns_df.reset_index().melt(
                        id_vars="Date",
                        var_name="Asset",
                        value_name="Daily Return"
                    ).dropna()
                    
                    # Clean return values to prevent huge outliers from distorting histogram
                    q_low = melted_returns["Daily Return"].quantile(0.01)
                    q_high = melted_returns["Daily Return"].quantile(0.99)
                    cleaned_returns = melted_returns[
                        (melted_returns["Daily Return"] >= q_low) & 
                        (melted_returns["Daily Return"] <= q_high)
                    ]
                    
                    fig_dist = px.histogram(
                        cleaned_returns,
                        x="Daily Return",
                        color="Asset",
                        barmode="overlay",
                        histnorm="probability density",
                        title="Returns Density Distribution (1st to 99th Percentile)",
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig_dist.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#e2e8f0"),
                        xaxis_title="Daily Return (%)",
                        yaxis_title="Probability Density"
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
                    st.caption("Distribution histograms representing returns frequency and skewness. Higher peaks at the center describe lower day-to-day variance, while fat tails reveal tail risk variance.")

        # =========================================================
        # TAB 4: MONOSPACE ALERTS BOARD
        # =========================================================
        with tab_alerts:
            st.subheader("🚨 Live Monospace UTBot Signals Alert Board")
            st.markdown("Scans the most recent market candles and outputs active trend indicators and stop loss thresholds.")
            
            alert_cols = st.columns(3)
            for idx, coin in enumerate(selected_coins):
                col_idx = idx % 3
                with alert_cols[col_idx]:
                    df = all_prices.get(coin)
                    if df is not None and not df.empty:
                        last_row = df.iloc[-1]
                        price = float(last_row["Close"])
                        atr_val = float(last_row["atr"])
                        trend_val = int(last_row["trend"])
                        
                        # Stop loss prices
                        stop_upper = float(last_row["upper"])
                        stop_lower = float(last_row["lower"])
                        
                        if trend_val == 1:
                            status_tag = '<div class="status-buy">🟢 BUY ALERT (BULLISH)</div>'
                            active_stop = stop_upper
                            stop_desc = "ATR Trailing Support"
                        else:
                            status_tag = '<div class="status-sell">🔴 SELL ALERT (BEARISH)</div>'
                            active_stop = stop_lower
                            stop_desc = "ATR Trailing Resistance"
                            
                        # Show card
                        st.markdown(f"""
                        <div style="background: rgba(30, 41, 59, 0.35); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 18px; margin-bottom: 15px;">
                            <div style="font-size: 16px; font-weight: bold; color: #f8fafc;" class="alert-header">♛ {coin}-USD Ticker</div>
                            <div style="font-size: 24px; font-weight: 700; color: #a29bfe; margin-top: 8px; font-family: monospace;">${price:,.2f}</div>
                            <div style="margin-top: 10px; margin-bottom: 15px;">{status_tag}</div>
                            <div style="font-size: 12px; color: #94a3b8; font-family: monospace;">
                                <b>ATR Volatility (10)</b>: ${atr_val:,.2f}<br>
                                <b>{stop_desc}</b>: ${active_stop:,.2f}<br>
                                <b>Last Updated</b>: {df.index[-1].strftime("%Y-%m-%d")}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info(f"Signal scan failed for {coin}-USD.")

# Auto-refresh checkbox
st.markdown("---")
st.caption("UTBot backtests and alert indicators represent historical simulations of rules-based indicators and do not constitute financial advice.")
