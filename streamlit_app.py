# (Updated code without rapidfuzz)
# Uses difflib instead of rapidfuzz to avoid extra dependencies

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from difflib import get_close_matches
from datetime import date
import requests
import hashlib

st.set_page_config(page_title="Universal Market App", layout="wide")

st.title("📊 Universal Stock & ETF Portfolio App")
st.markdown("Search by **name or ticker**, allocate capital, and run portfolio simulations.")

# ============================
# ✅ Premium AI Config
# ============================
API_URL = "https://universal-market-app-1.onrender.com"  # change to your deployed backend URL later

def user_id_from_email(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode()).hexdigest()

# ------------------ Run-state fix (graphs update with date changes) ------------------
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False

def trigger_run():
    st.session_state.run_analysis = True

# ------------------ Helpers ------------------

@st.cache_data(ttl=3600)
def load_nse_stock_list():
    import os
    import urllib.request
    
    local_path = "EQUITY_L.csv"
    if os.path.exists(local_path):
        df = pd.read_csv(local_path)
    elif os.path.exists("data/EQUITY_L.csv"):
        df = pd.read_csv("data/EQUITY_L.csv")
    else:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                df = pd.read_csv(response)
        except Exception:
            df = pd.DataFrame(columns=["SYMBOL", "NAME OF COMPANY"])
            
    df["SYMBOL"] = df["SYMBOL"].astype(str) + ".NS"
    return dict(zip(df["NAME OF COMPANY"].str.upper(), df["SYMBOL"]))

ETF_MAP = {
    "NIFTY 50 ETF": "NIFTYBEES.NS",
    "BANK NIFTY ETF": "BANKBEES.NS",
    "GOLD ETF": "GOLDBEES.NS",
    "IT ETF": "ITBEES.NS",
}

@st.cache_data(ttl=3600)
def resolve_assets(user_inputs):
    stock_map = load_nse_stock_list()
    resolved = {}
    for item in user_inputs:
        key = item.upper().strip()
        if "." in key:
            resolved[item] = key
        elif key in ETF_MAP:
            resolved[item] = ETF_MAP[key]
        else:
            matches = get_close_matches(key, stock_map.keys(), n=1, cutoff=0.6)
            resolved[item] = stock_map[matches[0]] if matches else None
    return resolved

@st.cache_data(ttl=300)
def load_prices(tickers, start, end):
    tickers = sorted(list(set(tickers)))
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame()
    data = data.dropna()
    data.index = pd.to_datetime(data.index)
    return data

def plot_financial_data(df, title):
    fig = px.line(title=title)
    for col in df.columns[1:]:
        fig.add_scatter(x=df['Date'], y=df[col], name=col)
    fig.update_traces(line_width=3)
    fig.update_layout({'plot_bgcolor': "white"})
    st.plotly_chart(fig, use_container_width=True)

def price_scaling(raw_prices_df):
    scaled_prices_df = raw_prices_df.copy()
    for i in raw_prices_df.columns[1:]:
        scaled_prices_df[i] = raw_prices_df[i] / raw_prices_df[i].iloc[0]
    return scaled_prices_df

# ------------------ Sidebar ------------------

app_mode = st.sidebar.selectbox("App Workspace Mode", ["📈 Portfolio Analyzer", "🔬 Quantitative Research Engine", "🧩 Modular Strategy Composer"], index=2)

if app_mode == "📈 Portfolio Analyzer":
    st.sidebar.header("Inputs")

    @st.cache_data(ttl=3600)
    def load_search_options():
        stock_map = load_nse_stock_list()
        return sorted(list(stock_map.keys()) + list(ETF_MAP.keys()))

    search_options = load_search_options()

    with st.sidebar.form("portfolio_form"):
        selected_assets = st.multiselect(
            "🔍 Search & select stocks / ETFs (recommended)",
            options=search_options,
            key="selected_assets"
        )

        manual_assets = st.text_input(
            "✍️ Or manually type names / tickers (comma separated)",
            "",
            key="manual_assets"
        )

        initial_amount = st.number_input(
            "💵 Capital (INR)",
            min_value=1000,
            max_value=10000000,
            value=100000,
            step=5000,
            key="initial_amount"
        )

        start_date = st.date_input(
            "📅 Start Date",
            date(2023, 1, 1),
            key="start_date"
        )

        end_date = st.date_input(
            "📅 End Date",
            date.today(),
            key="end_date"
        )

        run_mc = st.checkbox(
            "🎯 Run Monte Carlo Optimization",
            value=True,
            key="run_mc"
        )

        num_sims = st.number_input(
            "🔢 Number of Simulations",
            min_value=100,
            max_value=25000,
            value=2000,
            step=500,
            key="num_sims"
        )

        submit_button = st.form_submit_button("Run Analysis")
        if submit_button:
            trigger_run()

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔮 AI Prediction (Premium)")

    ai_enabled = st.sidebar.checkbox("Enable AI Prediction", key="ai_enabled", on_change=trigger_run)

    email = st.sidebar.text_input("Email (for premium access)", key="premium_email")

    horizon_map = {"5 Days": 5, "10 Days": 10, "20 Days": 20, "60 Days": 60}
    horizon_label = st.sidebar.selectbox("Horizon", list(horizon_map.keys()), index=1, key="ai_horizon", on_change=trigger_run)
    horizon_days = horizon_map[horizon_label]

# ------------------ Main ------------------

if app_mode == "📈 Portfolio Analyzer":
    if st.session_state.run_analysis:

        if end_date <= start_date:
            st.error("❌ End Date must be after Start Date")
            st.stop()

        user_assets = list(selected_assets) + [x.strip() for x in manual_assets.split(",") if x.strip()]
        if not user_assets:
            st.error("❌ Please select or enter at least one asset")
            st.stop()

        resolved = resolve_assets(user_assets)

        valid = {k: v for k, v in resolved.items() if v}
        invalid = [k for k, v in resolved.items() if not v]

        if invalid:
            st.warning(f"⚠️ Could not resolve: {', '.join(invalid)}")

        if not valid:
            st.error("❌ No valid assets resolved")
            st.stop()

        st.subheader("Resolved Assets")
        st.write(valid)

        tickers = list(valid.values())

        prices = load_prices(tickers, start_date, end_date)
        if prices.empty:
            st.error("❌ No price data fetched (try different dates / tickers)")
            st.stop()

        returns = prices.pct_change().dropna()

        # -------- Allocation --------
        weights = np.random.random(len(prices.columns))
        weights /= weights.sum()
        allocation = float(initial_amount) * weights

        alloc_df = pd.DataFrame({
            "Asset": prices.columns,
            "Weight": weights,
            "Allocation (INR)": allocation
        })

        st.subheader("💰 Portfolio Allocation")
        st.dataframe(alloc_df)

        # -------- Portfolio calcs --------
        portfolio_positions = (prices / prices.iloc[0]) * allocation
        portfolio_value = portfolio_positions.sum(axis=1)

        portfolio_df = portfolio_positions.copy()
        portfolio_df["Portfolio Value [$]"] = portfolio_value
        portfolio_df["Portfolio Daily Return [%]"] = portfolio_value.pct_change() * 100
        portfolio_df["Date"] = portfolio_df.index
        portfolio_df = portfolio_df[["Date"] + [c for c in portfolio_df.columns if c != "Date"]]

        # -------- Percentage Change (Scaled Prices) --------
        st.subheader("📊 Percentage Change (Scaled Prices)")
        scaled_prices_df = prices.copy()
        scaled_prices_df["Date"] = scaled_prices_df.index
        scaled_prices_df = scaled_prices_df[["Date"] + list(prices.columns)]
        scaled_prices_df = price_scaling(scaled_prices_df)
        plot_financial_data(scaled_prices_df, "Scaled Price Change (Base = 1.0)")

        # -------- Price Movement (Actual Prices) --------
        st.subheader("📈 Price Movement (Actual Prices)")
        raw_prices_df = prices.copy()
        raw_prices_df["Date"] = raw_prices_df.index
        raw_prices_df = raw_prices_df[["Date"] + list(prices.columns)]
        plot_financial_data(raw_prices_df, "Price Movement (Actual Prices)")

        # -------- Portfolio Positions --------
        st.subheader("💼 Portfolio Positions (INR)")
        plot_financial_data(
            portfolio_df.drop(['Portfolio Value [$]', 'Portfolio Daily Return [%]'], axis=1),
            'Portfolio positions [$]'
        )

        # -------- Portfolio Value Over Time --------
        st.subheader("💼 Total Portfolio Value Over Time")
        plot_financial_data(
            portfolio_df[['Date', 'Portfolio Value [$]']],
            'Total Portfolio Value [$]'
        )

        # -------- Daily Returns --------
        st.subheader("📉 Daily Returns (%)")
        daily_returns_df = returns * 100
        daily_returns_df["Date"] = daily_returns_df.index
        daily_returns_df = daily_returns_df[["Date"] + list(returns.columns)]
        plot_financial_data(daily_returns_df, 'Percentage Daily Returns [%]')

        # -------- Heatmap --------
        st.subheader("🔥 Correlation Heatmap")
        plt.figure(figsize=(10, 8))
        sns.heatmap(daily_returns_df.drop(columns=['Date']).corr(), annot=True)
        st.pyplot(plt.gcf())
        plt.close()

        # -------- Histogram --------
        st.subheader("📊 Daily % Change Distribution (Histogram)")
        fig = px.histogram(daily_returns_df.drop(columns=["Date"]))
        fig.update_layout({'plot_bgcolor': "white"})
        st.plotly_chart(fig, use_container_width=True)

        # -------- Monte Carlo (your exact plot + optimal point) --------
        if run_mc:
            st.subheader("🎯 Monte Carlo Simulation")

            mean_returns = returns.mean() * 252
            cov = returns.cov() * 252

            sim_results = []
            weight_list = []

            for _ in range(int(num_sims)):
                w = np.random.random(len(prices.columns))
                w /= w.sum()
                weight_list.append(w)

                port_return = float(np.dot(w, mean_returns))
                port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))
                sharpe = (port_return / port_vol) if port_vol != 0 else np.nan
                sim_results.append([port_return, port_vol, sharpe])

            sim_out_df = pd.DataFrame(sim_results, columns=["Portfolio_Return", "Volatility", "Sharpe_Ratio"])

            sharpe_series = sim_out_df["Sharpe_Ratio"].replace([np.inf, -np.inf], np.nan)
            optimal_idx = sharpe_series.idxmax()

            optimal_portfolio_return = float(sim_out_df.loc[optimal_idx, "Portfolio_Return"])
            optimal_volatility = float(sim_out_df.loc[optimal_idx, "Volatility"])

            fig = px.scatter(
                sim_out_df,
                x='Volatility',
                y='Portfolio_Return',
                color='Sharpe_Ratio',
                size='Sharpe_Ratio',
                hover_data=['Sharpe_Ratio']
            )
            fig.add_trace(go.Scatter(
                x=[optimal_volatility],
                y=[optimal_portfolio_return],
                mode='markers',
                name='Optimal Point',
                marker=dict(size=[40], color='red')
            ))
            fig.update_layout(coloraxis_colorbar=dict(y=0.7, dtick=5))
            fig.update_layout({'plot_bgcolor': "white"})
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("✅ Optimal Portfolio Weights (Max Sharpe)")
            best_df = pd.DataFrame({
                "Asset": prices.columns,
                "Weight": weight_list[int(optimal_idx)]
            })
            st.dataframe(best_df)

        # ============================
        # 🔮 Premium AI Prediction Panel (Main)
        # ============================
        if ai_enabled:
            st.markdown("---")
            st.subheader("🔮 AI Return Prediction (Premium)")

            if not email:
                st.warning("Enter your email in the sidebar to use the Premium AI feature.")
            else:
                user_id = user_id_from_email(email)

                # if multiple selected, let user choose; otherwise auto
                chosen_ticker = tickers[0]
                if len(tickers) > 1:
                    chosen_ticker = st.selectbox("Select asset for prediction", tickers, index=0)

                c1, c2 = st.columns(2)

                with c1:
                    if st.button("Unlock Premium (Pay)"):
                        try:
                            r = requests.post(
                                f"{API_URL}/billing/create-checkout-session",
                                json={"user_id": user_id, "email": email},
                                timeout=20
                            )
                            if r.ok:
                                st.link_button("Open Payment Link", r.json()["url"])
                            else:
                                st.error(r.text)
                        except Exception as e:
                            st.error(f"Payment error: {e}")

                with c2:
                    if st.button("Run AI Prediction"):
                        try:
                            r = requests.post(
                                f"{API_URL}/predict",
                                json={"user_id": user_id, "ticker": chosen_ticker, "horizon_days": horizon_days},
                                timeout=60
                            )
                            if r.ok:
                                out = r.json()
                                st.metric("Predicted Return", f"{out['predicted_return']*100:.2f}%")
                                st.write(
                                    f"Confidence Range: {out['ci_low']*100:.2f}% to {out['ci_high']*100:.2f}% "
                                    f"(Horizon: {out['horizon_days']} trading days)"
                                )
                                st.caption("Educational use only. Not financial advice.")
                            else:
                                st.error(r.text)
                        except Exception as e:
                            st.error(f"Prediction error: {e}")

    else:
        st.info("👈 Select assets / change dates — graphs will auto-update. (You can also click Run Analysis.)")

elif app_mode == "🔬 Quantitative Research Engine":
    # 🔬 Quantitative Research Engine Workspace Mode
    st.title("🔬 Antigravity Quantitative Research Engine")
    st.markdown("A self-improving quantitative research platform that discovers market structure, projects manifolds, identifies regimes, and leaderboards alpha features.")

    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity_ai_brain"))
    
    from research_engine import (
        QuantitativeResearchEngine, FeatureEngine, LabelEngine,
        ManifoldRepresentation, ClusterDiscovery, RegimeDetector,
        CrossSectionalRanker, NetworkAnalyzer, MetaModel
    )

    # 1. Controls
    st.header("⚡ Data Warehouse Ingestion & Discovery")
    default_tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "RELIANCE.NS", "TCS.NS", "INFY.NS", "AAPL", "MSFT", "GOOG", "TSLA"]
    research_tickers = st.text_input("Enter research assets (comma-separated tickers)", ", ".join(default_tickers))
    index_ticker = st.text_input("Benchmark Index Ticker", "^GSPC")

    col_dates1, col_dates2 = st.columns(2)
    with col_dates1:
        res_start = st.date_input("Start Date", date(2023, 1, 1), key="res_start")
    with col_dates2:
        res_end = st.date_input("End Date", date.today(), key="res_end")

    if st.button("Run Alpha Discovery Cycle"):
        with st.spinner("Processing Stage 1-10 Pipeline (Fetching, labeling, clustering, and computing correlation networks)..."):
            try:
                engine = QuantitativeResearchEngine()
                ticker_list = [x.strip() for x in research_tickers.split(",") if x.strip()]
                leaders = engine.run_nightly_research_cycle(ticker_list, index_ticker=index_ticker)
                st.success("✅ Nightly Research Cycle completed! Database warehouse updated.")
            except Exception as e:
                st.error(f"Error executing research cycle: {e}")

    # Load SQLite warehouse data
    import sqlite3
    db_path = "research_warehouse.db"

    if not os.path.exists(db_path):
        st.info("ℹ️ SQLite data warehouse is currently empty. Click 'Run Alpha Discovery Cycle' above to populate the database with historical stock and crypto features.")
    else:
        conn = sqlite3.connect(db_path)
        try:
            obs_df = pd.read_sql_query("SELECT * FROM market_observations", conn)
            labels_df = pd.read_sql_query("SELECT * FROM future_labels", conn)
            leader_df = pd.read_sql_query("SELECT * FROM feature_leaderboard ORDER BY score DESC", conn)
        except Exception as e:
            st.error(f"Error reading database: {e}")
            obs_df = pd.DataFrame()
            labels_df = pd.DataFrame()
            leader_df = pd.DataFrame()
        conn.close()

        if not obs_df.empty and not labels_df.empty:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🌌 Manifold & Clustering", 
                "📊 Cross-Sectional Ranking", 
                "🏭 Feature Leaderboard", 
                "🕸️ Correlation Network", 
                "⚖️ Meta-Model Sizing"
            ])

            # TAB 1: Manifold & Clustering
            with tab1:
                st.header("🌌 Geometric Market Manifold & Clustering")
                st.markdown("Projecting high-dimensional price, volume, and volatility space into 2D PCA representation.")

                # Scale features for PCA
                cluster_cols = [
                    "returns", "log_returns", "vol_zscore", "rel_volume", 
                    "dollar_volume", "atr", "atr_zscore", "realized_vol", 
                    "vol_percentile", "dist_20dma", "dist_50dma", "dist_200dma", 
                    "momentum_5d", "momentum_20d", "momentum_60d", "drawdown", 
                    "relative_strength", "beta", "correlation_index"
                ]

                # Center data
                X = obs_df[cluster_cols].fillna(0.0).values
                projection = ManifoldRepresentation.reduce_dimensions_pca(X, n_components=2)
                
                # Fetch cluster stats
                # Re-run clustering locally on the retrieved SQLite dataset to assign clusters
                cluster_stats, cluster_labels = ClusterDiscovery.find_clusters(
                    obs_df[cluster_cols].fillna(0.0), labels_df, n_clusters=5
                )

                plot_df = pd.DataFrame(projection, columns=["PCA 1", "PCA 2"])
                plot_df["Cluster ID"] = [f"Cluster {c}" for c in cluster_labels[:len(plot_df)]]
                
                # Map future returns
                common_len = min(len(plot_df), len(labels_df))
                plot_df["Future 20D Return (%)"] = labels_df["future_ret_20d"].iloc[:common_len].values * 100
                plot_df["Ticker"] = obs_df["ticker"].iloc[:common_len].values
                plot_df["Date"] = obs_df["date"].iloc[:common_len].values

                color_option = st.selectbox("Color Manifold Points By:", ["Cluster ID", "Future 20D Return (%)"])
                
                fig_scatter = px.scatter(
                    plot_df, x="PCA 1", y="PCA 2", color=color_option,
                    hover_data=["Ticker", "Date", "Future 20D Return (%)"],
                    title="2D Manifold Space Projection"
                )
                fig_scatter.update_layout(plot_bgcolor="white")
                st.plotly_chart(fig_scatter, use_container_width=True)

                st.subheader("🏆 Cluster Discovery Leaderboard")
                rows = []
                for c_id, stats in cluster_stats.items():
                    rows.append({
                        "Cluster ID": f"Cluster {c_id}",
                        "Observation Count": stats["count"],
                        "Win Rate (%)": f"{stats['win_rate']*100:.2f}%",
                        "Average Future Return (%)": f"{stats['avg_return']*100:.2f}%",
                        "Average Max Drawdown (%)": f"{stats['max_drawdown']*100:.2f}%",
                        "Proxy Sharpe Ratio": f"{stats['sharpe_ratio']:.2f}"
                    })
                st.table(pd.DataFrame(rows))

                # Highlight best cluster
                best_c = max(cluster_stats.items(), key=lambda x: x[1]["avg_return"])
                st.success(f"🔥 **Top Discovered Alpha Region**: Cluster {best_c[0]} (Expected 20D Return: {best_c[1]['avg_return']*100:.2f}%)")

            # TAB 2: Cross-Sectional Ranking
            with tab2:
                st.header("📊 Universe Cross-Sectional Ranking")
                st.markdown("Ranks the active universe according to expectations computed from current cluster centroids.")

                # Pivot latest dates
                latest_rows = {}
                tickers = obs_df["ticker"].unique()
                for ticker in tickers:
                    ticker_df = obs_df[obs_df["ticker"] == ticker]
                    if not ticker_df.empty:
                        latest_rows[ticker] = ticker_df

                rankings = CrossSectionalRanker.rank_assets(latest_rows, cluster_stats)
                
                rank_df = pd.DataFrame(rankings)
                rank_df["Win Rate (%)"] = rank_df["win_rate"] * 100
                rank_df["Expected 20D Return (%)"] = rank_df["expected_return"] * 100
                rank_df["Max Drawdown (%)"] = rank_df["drawdown"] * 100
                rank_df["Regime"] = [
                    RegimeDetector.detect_regime(row["realized_vol"], row["dist_200dma"])
                    for _, row in rank_df.iterrows()
                ]

                rank_disp = rank_df[[
                    "ticker", "cluster", "Expected 20D Return (%)", "Win Rate (%)", 
                    "Max Drawdown (%)", "sharpe", "Regime"
                ]].rename(columns={
                    "ticker": "Ticker",
                    "cluster": "Cluster ID",
                    "sharpe": "Sharpe Ratio"
                })
                
                st.dataframe(rank_disp.style.highlight_max(subset=["Expected 20D Return (%)"], color="lightgreen"))

            # TAB 3: Feature Leaderboard
            with tab3:
                st.header("🏭 Research Factory Feature Leaderboard")
                st.markdown(" Leaderboard of synthesized features generated by random math mutations (Stage 7).")
                if not leader_df.empty:
                    st.dataframe(leader_df)
                else:
                    st.info("Run feature mutations in a cycle to populate the leaderboard.")

            # TAB 4: Correlation Network
            with tab4:
                st.header("🕸️ Correlation Network & Leadership Analysis")
                # Build network from price_df or query from sqlite
                tickers = obs_df["ticker"].unique()
                if len(tickers) > 1:
                    pivoted = obs_df.pivot(index="date", columns="ticker", values="close").dropna()
                    if not pivoted.empty and len(pivoted) > 5:
                        corr_matrix = pivoted.pct_change().corr().fillna(0.0)
                        
                        # Define circle layout coordinates
                        num_nodes = len(tickers)
                        angles = np.linspace(0, 2 * np.pi, num_nodes, endpoint=False)
                        pos = {tickers[i]: (np.cos(angles[i]), np.sin(angles[i])) for i in range(num_nodes)}
                        
                        # Create edges trace
                        edge_x = []
                        edge_y = []
                        
                        threshold = st.slider("Correlation Connection Threshold", 0.1, 0.9, 0.4, key="corr_thresh")
                        
                        for i in range(num_nodes):
                            for j in range(i + 1, num_nodes):
                                corr = corr_matrix.iloc[i, j]
                                if abs(corr) >= threshold:
                                    t1, t2 = tickers[i], tickers[j]
                                    x0, y0 = pos[t1]
                                    x1, y1 = pos[t2]
                                    edge_x.extend([x0, x1, None])
                                    edge_y.extend([y0, y1, None])
                                    
                        edge_trace = go.Scatter(
                            x=edge_x, y=edge_y,
                            line=dict(width=2, color='#c8c8c8'),
                            hoverinfo='none',
                            mode='lines'
                        )
                        
                        # Create nodes trace
                        node_x = []
                        node_y = []
                        node_text = []
                        for node in tickers:
                            x, y = pos[node]
                            node_x.append(x)
                            node_y.append(y)
                            node_text.append(node)
                            
                        node_trace = go.Scatter(
                            x=node_x, y=node_y,
                            mode='markers+text',
                            text=node_text,
                            textposition="top center",
                            hoverinfo='text',
                            marker=dict(
                                showscale=True,
                                colorscale='Viridis',
                                reversescale=True,
                                color=[],
                                size=25,
                                colorbar=dict(
                                    thickness=15,
                                    title='Centrality score',
                                    xanchor='left',
                                    titleside='right'
                                ),
                                line_width=2
                            )
                        )
                        
                        # Compute degree centrality for node coloring
                        centralities = []
                        for t1 in tickers:
                            deg = sum(1 for t2 in tickers if t1 != t2 and abs(corr_matrix.loc[t1, t2]) >= threshold)
                            centralities.append(deg)
                        node_trace.marker.color = centralities
                        
                        fig_net = go.Figure(data=[edge_trace, node_trace],
                                         layout=go.Layout(
                                            title='Interactive Asset Correlation Network',
                                            titlefont_size=16,
                                            showlegend=False,
                                            hovermode='closest',
                                            margin=dict(b=20,l=5,r=5,t=40),
                                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                            plot_bgcolor='white'
                                         ))
                        st.plotly_chart(fig_net, use_container_width=True)
                        
                        # Leadership centrality rankings
                        st.subheader("👑 Market Leaders Centrality Table")
                        centrality_df = pd.DataFrame({
                            "Ticker": tickers,
                            "Degree Connection Count": centralities
                        }).sort_values(by="Degree Connection Count", ascending=False)
                        st.dataframe(centrality_df)

            # TAB 5: Meta-Model Kelly Sizing
            with tab5:
                st.header("⚖️ Meta-Model Sizing & Position Allocation")
                st.markdown("Calculates sizing according to Kelly Criterion scaled by cluster confidence score.")

                target_asset = st.selectbox("Select Target Asset:", tickers)
                capital = st.number_input("Portfolio Capital (USD)", min_value=100, value=10000)
                confidence = st.slider("Model Confidence Score", 0.0, 1.0, 0.8)

                # Look up stats of the chosen asset's cluster
                latest_df = rank_df[rank_df["ticker"] == target_asset]
                if not latest_df.empty:
                    c_id = latest_df["cluster"].iloc[0]
                    c_win = latest_df["win_rate"].iloc[0]
                    # Estimate payout ratio based on max gain/loss
                    c_stats = cluster_stats[c_id]
                    payout = abs(c_stats["avg_return"] / (c_stats["max_drawdown"] + 1e-9))
                    if payout <= 0.0:
                        payout = 1.5

                    sizing_res = MetaModel.compute_position_size(c_win, payout, capital, confidence)
                    
                    st.subheader(f"Allocation for {target_asset}")
                    st.write(f"**Discovered Cluster**: Cluster {c_id}")
                    st.write(f"**Cluster Win Rate**: {c_win*100:.2f}%")
                    st.write(f"**Estimated Payout Ratio**: {payout:.2f}x")
                    
                    col_met1, col_met2, col_met3 = st.columns(3)
                    with col_met1:
                        st.metric("Raw Kelly Fraction", f"{sizing_res['kelly_fraction']*100:.2f}%")
                    with col_met2:
                        st.metric("Risk-Adjusted Fraction", f"{sizing_res['final_fraction']*100:.2f}%")
                    with col_met3:
                        st.metric("Target Sizing Allocation", f"${sizing_res['position_size_usd']:.2f}")
                else:
                    st.warning("Asset ranking stats not loaded yet.")

                plot_df = pd.DataFrame({
                    "Date": df.index,
                    "Strategy": df['Strategy_Equity'],
                    "Buy & Hold": df['Buy_Hold_Equity']
                })
                fig = px.line(plot_df, x="Date", y=["Strategy", "Buy & Hold"], title="Modular Strategy vs Buy & Hold ($1,000 Initial)")
                fig.update_layout(plot_bgcolor="white", yaxis_title="Portfolio Value ($)")
                st.plotly_chart(fig, use_container_width=True)

                # Metrics
                strat_ret = (df['Strategy_Equity'].iloc[-1] / 1000 - 1) * 100
                bh_ret = (df['Buy_Hold_Equity'].iloc[-1] / 1000 - 1) * 100
                
                strat_dd = ((df['Strategy_Equity'] / df['Strategy_Equity'].cummax()) - 1).min() * 100
                bh_dd = ((df['Buy_Hold_Equity'] / df['Buy_Hold_Equity'].cummax()) - 1).min() * 100

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Strategy Total Return", f"{strat_ret:.2f}%")
                    st.metric("Strategy Max Drawdown", f"{strat_dd:.2f}%")
                with col2:
                    st.metric("Buy & Hold Total Return", f"{bh_ret:.2f}%")
                    st.metric("Buy & Hold Max Drawdown", f"{bh_dd:.2f}%")
