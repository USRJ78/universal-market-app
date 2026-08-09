import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from option_engine import (
    scan_market,
    monte_carlo_simulation
)

# -------------------------------
# PAGE
# -------------------------------
st.set_page_config(
    page_title="Options Arbitrage Scanner",
    layout="wide"
)

st.title("📈 Options Arbitrage Scanner")
st.caption("Benjamin Graham + Black Scholes + Monte Carlo")

# -------------------------------
# LOAD NSE STOCKS
# -------------------------------
@st.cache_data
def load_tickers():
    df = pd.read_csv("data/EQUITY_L.csv")

    symbols = (
        df["SYMBOL"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    tickers = []

    for symbol in symbols:
        if "&" in symbol:
            continue
        tickers.append(symbol + ".NS")

    return tickers


tickers = load_tickers()

# -------------------------------
# SIDEBAR INPUTS
# -------------------------------
st.sidebar.header("Settings")

mode = st.sidebar.selectbox(
    "Mode",
    ["Live Scan", "Backtest Approximation"]
)

capital = st.sidebar.number_input(
    "Capital",
    min_value=10000,
    value=100000,
    step=10000
)

max_positions = st.sidebar.slider(
    "Max Positions",
    1,
    20,
    5
)

simulation_runs = st.sidebar.slider(
    "Monte Carlo Simulations",
    100,
    5000,
    1000
)

expected_return = st.sidebar.slider(
    "Expected Annual Return %",
    -50,
    100,
    15
) / 100

volatility = st.sidebar.slider(
    "Annual Volatility %",
    5,
    100,
    25
) / 100

scan_button = st.sidebar.button("Run Scan")

# -------------------------------
# RUN
# -------------------------------
if scan_button:

    with st.spinner("Scanning market..."):
        results = scan_market(tickers, capital)

    if results.empty:
        st.warning("No opportunities found.")
        st.stop()

    # -------------------------------
    # TOP TRADES
    # -------------------------------
    st.subheader("Best Option Opportunities")

    display_cols = [
        "symbol",
        "type",
        "strike",
        "expiry",
        "market_price",
        "theoretical_price",
        "edge",
        "lots",
        "capital_used",
        "spot_price",
        "intrinsic"
    ]

    st.dataframe(results[display_cols].head(max_positions))

    # -------------------------------
    # CAPITAL USAGE
    # -------------------------------
    total_used = results["capital_used"].head(max_positions).sum()
    remaining = capital - total_used

    col1, col2, col3 = st.columns(3)

    col1.metric("Initial Capital", f"₹{capital:,.0f}")
    col2.metric("Capital Used", f"₹{total_used:,.0f}")
    col3.metric("Remaining Cash", f"₹{remaining:,.0f}")

    # -------------------------------
    # ESTIMATED PROFIT
    # -------------------------------
    selected = results.head(max_positions).copy()

    selected["Estimated Profit"] = (
        (selected["theoretical_price"] - selected["market_price"])
        * selected["lot_size"]
        * selected["lots"]
    )

    st.subheader("Estimated Trade Profit")
    st.dataframe(
        selected[
            [
                "symbol",
                "type",
                "expiry",
                "lots",
                "capital_used",
                "Estimated Profit"
            ]
        ]
    )

    total_profit = selected["Estimated Profit"].sum()

    st.metric(
        "Estimated Total Arbitrage Profit",
        f"₹{total_profit:,.2f}"
    )

    # -------------------------------
    # MONTE CARLO
    # -------------------------------
    st.subheader("Monte Carlo Capital Simulation")

    final_capital = capital + total_profit

    sim_results, summary = monte_carlo_simulation(
        final_capital,
        expected_return,
        volatility,
        simulations=simulation_runs,
        days=30
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Worst Case", f"₹{summary['worst_case']:,.0f}")
    c2.metric("Expected", f"₹{summary['expected_case']:,.0f}")
    c3.metric("Best Case", f"₹{summary['best_case']:,.0f}")
    c4.metric("Loss Probability", f"{summary['loss_probability']*100:.1f}%")

    # -------------------------------
    # HISTOGRAM
    # -------------------------------
    fig, ax = plt.subplots()
    ax.hist(sim_results, bins=50)
    ax.set_title("Monte Carlo Distribution")
    ax.set_xlabel("Final Capital")
    ax.set_ylabel("Frequency")

    st.pyplot(fig)

    # -------------------------------
    # RISK NOTE
    # -------------------------------
    st.subheader("Risk Intervention")

    risk_msg = """
    Capital protection logic:
    - Maximum 10% capital per trade
    - Automatic diversification
    - Only undervalued stocks
    - Only underpriced options
    - Dynamic rotation into stronger opportunities
    - Monte Carlo downside analysis
    """

    st.info(risk_msg)