# pages/3D_Charts.py
# Enhanced 3D Stock Visualizer — Time x Price x Pressure
# Overlays: Peak/Trough detection, Fibonacci planes, Nakshatra coloring,
#           EMA-200 (Graham proxy), ATR Stop, Multi-strategy entry signals

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
import os

st.set_page_config(page_title="3D Strategy Visualizer", layout="wide")

st.markdown("""
<style>
body { background: #0a0e14; }
.stApp { background: #0a0e14; }
</style>
""", unsafe_allow_html=True)

st.title("3D Strategy Visualizer - Time x Price x Pressure")
st.caption("Peak/Trough detection | Fibonacci zones | Nakshatra signals | EMA-200 | ATR Stop | Multi-strategy overlays")

# Load NSE Equity Master
@st.cache_data
def load_equity_master():
    base_path = os.path.dirname(os.path.dirname(__file__))
    for fname in ["data/EQUITY_L.csv", "EQUITY_L.csv"]:
        fp = os.path.join(base_path, fname)
        if os.path.exists(fp):
            df = pd.read_csv(fp)
            df = df.dropna(subset=["SYMBOL"])
            df["Ticker"] = df["SYMBOL"].astype(str) + ".NS"
            return df
    st.error("EQUITY_L.csv not found.")
    st.stop()

equity_df = load_equity_master()

# Sidebar
with st.sidebar:
    st.header("Chart Settings")
    ticker = st.selectbox("Select Ticker", options=sorted(equity_df["Ticker"].unique()))
    period = st.selectbox("Lookback Period", ["6mo", "1y", "2y", "5y"], index=1)
    y_mode = st.selectbox("Y-Axis", ["Close Price", "Log Close"], index=0)
    pressure_mode = st.selectbox(
        "Z-Axis (Pressure Variable)",
        ["Rolling Volatility (21D, Annualized %)", "Volume Z-Score (20D)", "RSI (14)", "Drawdown (252D high)", "ATR Trailing Stop Distance %"],
        index=2
    )
    st.divider()
    st.header("Strategy Overlays")
    show_peaks     = st.toggle("Peaks and Troughs",         value=True)
    show_fib       = st.toggle("Fibonacci Planes",          value=True)
    show_nakshatra = st.toggle("Nakshatra Signal Colors",   value=True)
    show_ema200    = st.toggle("EMA-200 (Graham Proxy)",    value=True)
    show_atr_stop  = st.toggle("ATR Trailing Stop",         value=True)
    show_signals   = st.toggle("Multi-Strategy Signals",    value=True)
    peak_window    = st.slider("Peak/Trough Window (bars)", 5, 30, 10)

# Helpers
def to_series(x):
    if isinstance(x, pd.DataFrame):
        return x.iloc[:, 0]
    return x.squeeze()

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def ema(series, period=200):
    return series.ewm(span=period, adjust=False).mean()

def calc_atr(df, period=14):
    h = to_series(df["High"])
    l = to_series(df["Low"])
    c = to_series(df["Close"])
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def detect_peaks_troughs(series, window=10):
    peaks, troughs = [], []
    for i in range(window, len(series) - window):
        sl = series.iloc[i - window: i + window + 1]
        if series.iloc[i] == sl.max():
            peaks.append(i)
        elif series.iloc[i] == sl.min():
            troughs.append(i)
    return peaks, troughs

def fibonacci_levels(high, low):
    diff = high - low
    return {
        "0.0%": high, "23.6%": high - 0.236*diff, "38.2%": high - 0.382*diff,
        "50.0%": high - 0.500*diff, "61.8%": high - 0.618*diff,
        "78.6%": high - 0.786*diff, "88.6%": high - 0.886*diff, "100.0%": low
    }

# Nakshatra Engine
BULLISH_NAKSHATRAS = {"Rohini","Mrigashira","Pushya","Hasta","Chitra","Swati","Anuradha","Uttara Ashadha","Shravana","Revati"}
BEARISH_NAKSHATRAS = {"Bharani","Krittika","Ardra","Ashlesha","Magha","Purva Phalguni","Vishakha","Jyeshtha","Mula","Purva Ashadha"}
NAKSHATRA_NAMES = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]

def get_julian_date(dt):
    y, m = dt.year, dt.month
    d = dt.day + dt.hour / 24.0
    if m <= 2:
        y -= 1; m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + B - 1524.5

def get_nakshatra_signal(date):
    try:
        import datetime as _dt
        dt = _dt.datetime(date.year, date.month, date.day, 12, 0, 0)
        JD = get_julian_date(dt)
        T = (JD - 2451545.0) / 36525.0
        M_prime = 134.9633964 + 477198.8675055 * T
        D = 297.8501921 + 445267.1114034 * T
        M = 357.5291092 + 35999.0502909 * T
        F = 93.2720950 + 483202.0175233 * T
        L_prime = 218.3164477 + 481267.88123421 * T
        d_lam = (6.289*math.sin(math.radians(M_prime%360)) + 1.274*math.sin(math.radians((2*D-M_prime)%360)) + 0.658*math.sin(math.radians((2*D)%360)) + 0.214*math.sin(math.radians((2*M_prime)%360)) - 0.186*math.sin(math.radians(M%360)) - 0.114*math.sin(math.radians((2*F)%360)))
        tropical_lon = (L_prime + d_lam) % 360
        ayanamsa = 23.85 + 0.01396 * (date.year - 2000)
        sidereal_lon = (tropical_lon - ayanamsa) % 360
        idx = min(int(sidereal_lon / (360.0 / 27.0)), 26)
        name = NAKSHATRA_NAMES[idx]
        if name in BULLISH_NAKSHATRAS: return "BULL", name
        elif name in BEARISH_NAKSHATRAS: return "BEAR", name
        return "NEUTRAL", name
    except Exception:
        return "NEUTRAL", "Unknown"

@st.cache_data(ttl=900)
def load_ohlcv(ticker, period):
    df = yf.download(ticker, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

@st.cache_data(show_spinner=False)
def compute_nakshatra_colors(dates_str):
    import datetime as _dt
    color_map = {"BULL": "#00d4aa", "BEAR": "#ff4b6e", "NEUTRAL": "#8888aa"}
    signals, names, colors = [], [], []
    for ds in dates_str:
        d = _dt.date.fromisoformat(ds)
        sig, name = get_nakshatra_signal(d)
        signals.append(sig); names.append(name); colors.append(color_map[sig])
    return signals, names, colors

with st.spinner(f"Loading {ticker}..."):
    df = load_ohlcv(ticker, period)

if df.empty:
    st.error("No data found for selected ticker.")
    st.stop()

close  = to_series(df["Close"])
volume = to_series(df["Volume"])

returns   = close.pct_change() * 100
ema200    = ema(close, 200)
rsi14     = rsi(close, 14)
atr14     = calc_atr(df, 14)
atr_stop  = close - atr14 * 2.5
atr_pct   = (atr14 * 2.5 / close) * 100
roll_max  = close.rolling(252).max()
drawdown  = (close / roll_max - 1) * 100
vol21     = close.pct_change().rolling(21).std() * np.sqrt(252) * 100
vol_zscore = (volume - volume.rolling(20).mean()) / volume.rolling(20).std()

y = np.log(close) if y_mode == "Log Close" else close
y_label = "Log(Close)" if y_mode == "Log Close" else "Close (Rs)"

pressure_map = {
    "Rolling Volatility (21D, Annualized %)": (vol21, "Volatility %"),
    "Volume Z-Score (20D)": (vol_zscore, "Volume Z"),
    "RSI (14)": (rsi14, "RSI"),
    "Drawdown (252D high)": (drawdown, "Drawdown %"),
    "ATR Trailing Stop Distance %": (atr_pct, "ATR Stop %"),
}
z_raw, z_label = pressure_map[pressure_mode]

plot_df = pd.DataFrame({
    "Date": df.index, "Close": close, "Y": to_series(y), "Z": to_series(z_raw),
    "RSI": rsi14, "VolZ": vol_zscore, "EMA200": ema200, "ATRStop": atr_stop,
    "Drawdown": drawdown, "Returns": returns, "ATRPct": atr_pct,
}).dropna()
plot_df["t"] = np.arange(len(plot_df))

dates_str = [str(d.date()) for d in plot_df["Date"]]
nak_signals, nak_names, nak_colors = compute_nakshatra_colors(dates_str)
plot_df["NakSignal"] = nak_signals
plot_df["NakName"]   = nak_names

period_high = float(plot_df["Close"].max())
period_low  = float(plot_df["Close"].min())
fibs = fibonacci_levels(period_high, period_low)
peaks, troughs = detect_peaks_troughs(plot_df["Close"], window=peak_window)

def detect_signals(df, fibs):
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]
        fib618 = fibs["61.8%"]; fib382 = fibs["38.2%"]; fib886 = fibs["88.6%"]
        near_61 = abs(row["Close"]-fib618)/fib618 < 0.015
        near_38 = abs(row["Close"]-fib382)/fib382 < 0.015
        near_88 = abs(row["Close"]-fib886)/fib886 < 0.015
        sig_type = strategy = None
        if near_88 and row["RSI"] < 35:
            sig_type = "BUY"; strategy = "Hyper-Leverage (0.886 Fib + Capitulation)"
        elif near_61 and row["RSI"] < 40 and row["NakSignal"] == "BULL":
            sig_type = "BUY"; strategy = "Market Geometry (61.8% Fib + Nakshatra)"
        elif near_38 and row["RSI"] < 50 and row["NakSignal"] == "BULL":
            sig_type = "BUY"; strategy = "Market Geometry (38.2% Fib)"
        elif row.get("VolZ", 0) and row["VolZ"] > 2.0 and row["RSI"] < 35:
            sig_type = "BUY"; strategy = "Vol Spike + RSI Oversold"
        elif row["RSI"] > 70 and row["NakSignal"] == "BEAR":
            sig_type = "SELL"; strategy = "Nakshatra Exit (RSI Overbought + BEAR)"
        elif i > 0 and row["Close"] < row["ATRStop"]:
            sig_type = "STOP"; strategy = "ATR Trailing Stop Breach"
        if sig_type:
            signals.append({"t": row["t"], "Y": row["Y"], "Z": row["Z"],
                             "Close": row["Close"], "Date": row["Date"],
                             "Signal": sig_type, "Strategy": strategy, "RSI": row["RSI"]})
    return pd.DataFrame(signals)

signal_df = detect_signals(plot_df, fibs)

# ---- 3D FIGURE ----
fig = go.Figure()

if show_nakshatra:
    for sig, col, label in [("BULL","#00d4aa","Bullish Nakshatra"),("BEAR","#ff4b6e","Bearish Nakshatra"),("NEUTRAL","#8888aa","Neutral Nakshatra")]:
        mask = plot_df["NakSignal"] == sig
        sub = plot_df[mask]
        if sub.empty: continue
        fig.add_trace(go.Scatter3d(
            x=sub["t"], y=sub["Y"], z=sub["Z"],
            mode="markers", marker=dict(size=2.5, color=col, opacity=0.8),
            name=label,
            hovertemplate="Date: %{customdata[0]}<br>Close: Rs%{customdata[1]:.2f}<br>"+z_label+": %{z:.2f}<br>Nakshatra: %{customdata[2]}<extra></extra>",
            customdata=np.column_stack((sub["Date"].dt.strftime("%Y-%m-%d"), sub["Close"], sub["NakName"]))
        ))
else:
    fig.add_trace(go.Scatter3d(
        x=plot_df["t"], y=plot_df["Y"], z=plot_df["Z"],
        mode="lines+markers",
        marker=dict(size=2.5, color=plot_df["Z"], colorscale="Plasma", showscale=True),
        line=dict(width=2, color="rgba(100,160,255,0.4)"), name="Price Path"
    ))

if show_ema200:
    em_df = plot_df.dropna(subset=["EMA200"])
    ema_y = np.log(em_df["EMA200"]) if y_mode == "Log Close" else em_df["EMA200"]
    fig.add_trace(go.Scatter3d(x=em_df["t"], y=ema_y, z=em_df["Z"], mode="lines",
        line=dict(color="#FFD700", width=4), name="EMA-200 (Graham Proxy)",
        hovertemplate="EMA-200: Rs%{customdata:.2f}<extra></extra>", customdata=em_df["EMA200"]))

if show_atr_stop:
    atr_y = np.log(plot_df["ATRStop"].clip(lower=1)) if y_mode == "Log Close" else plot_df["ATRStop"]
    fig.add_trace(go.Scatter3d(x=plot_df["t"], y=atr_y, z=plot_df["Z"], mode="lines",
        line=dict(color="#ff6b35", width=2, dash="dash"), name="ATR Stop (2.5x)",
        hovertemplate="ATR Stop: Rs%{customdata:.2f}<extra></extra>", customdata=plot_df["ATRStop"]))

if show_fib:
    fib_colors = {"38.2%":"#4fc3f7","50.0%":"#81d4fa","61.8%":"#00e5ff","78.6%":"#40c4ff","88.6%":"#ff6090"}
    t_min, t_max = float(plot_df["t"].min()), float(plot_df["t"].max())
    z_mid = float(plot_df["Z"].median())
    for label, price in fibs.items():
        if label not in fib_colors: continue
        fib_y = math.log(price) if y_mode == "Log Close" else price
        fig.add_trace(go.Scatter3d(x=[t_min, t_max], y=[fib_y, fib_y], z=[z_mid, z_mid],
            mode="lines+text", line=dict(color=fib_colors[label], width=3),
            text=[f"Fib {label} Rs{price:,.0f}", ""], textposition="top left",
            textfont=dict(size=9, color=fib_colors[label]), name=f"Fib {label}", showlegend=True))

if show_peaks:
    if peaks:
        pk = plot_df.iloc[peaks]
        fig.add_trace(go.Scatter3d(x=pk["t"], y=pk["Y"], z=pk["Z"], mode="markers+text",
            marker=dict(size=8, color="#ff4b6e", symbol="diamond", line=dict(width=1, color="white")),
            text=["PEAK"]*len(pk), textfont=dict(size=8, color="#ff4b6e"), name="Peaks",
            hovertemplate="PEAK: Rs%{customdata:.2f}<extra></extra>", customdata=pk["Close"]))
    if troughs:
        tr = plot_df.iloc[troughs]
        fig.add_trace(go.Scatter3d(x=tr["t"], y=tr["Y"], z=tr["Z"], mode="markers+text",
            marker=dict(size=8, color="#00e676", symbol="diamond", line=dict(width=1, color="white")),
            text=["TROUGH"]*len(tr), textfont=dict(size=8, color="#00e676"), name="Troughs",
            hovertemplate="TROUGH: Rs%{customdata:.2f}<extra></extra>", customdata=tr["Close"]))

if show_signals and not signal_df.empty:
    for sig_type, color, sym in [("BUY","#00ff88","circle"),("SELL","#ff4b6e","cross"),("STOP","#ff8800","x")]:
        sub = signal_df[signal_df["Signal"] == sig_type]
        if sub.empty: continue
        fig.add_trace(go.Scatter3d(x=sub["t"], y=sub["Y"], z=sub["Z"], mode="markers",
            marker=dict(size=12, color=color, symbol=sym, line=dict(width=2, color="white")),
            name=f"{sig_type} Signals",
            hovertemplate="<b>"+sig_type+"</b><br>Date: %{customdata[0]}<br>Close: Rs%{customdata[1]:.2f}<br>Strategy: %{customdata[2]}<br>RSI: %{customdata[3]:.1f}<extra></extra>",
            customdata=np.column_stack((sub["Date"].dt.strftime("%Y-%m-%d"), sub["Close"], sub["Strategy"], sub["RSI"]))))

fig.update_layout(height=720,
    title=dict(text=f"{ticker} - 3D: Time x {y_label} x {z_label}", font=dict(size=18, color="white")),
    paper_bgcolor="#0a0e14",
    scene=dict(bgcolor="#0a0e14",
        xaxis=dict(title="Time Index", color="white", showgrid=True, gridcolor="#1a2035"),
        yaxis=dict(title=y_label, color="white", showgrid=True, gridcolor="#1a2035"),
        zaxis=dict(title=z_label, color="white", showgrid=True, gridcolor="#1a2035")),
    legend=dict(font=dict(color="white", size=10), bgcolor="rgba(10,14,20,0.8)", bordercolor="#2a3a5c", borderwidth=1),
    margin=dict(l=0, r=0, t=50, b=0))

st.plotly_chart(fig, use_container_width=True)

# Signal Summary
if show_signals and not signal_df.empty:
    st.divider()
    st.subheader("Strategy Signal Summary")
    buys  = signal_df[signal_df["Signal"] == "BUY"]
    sells = signal_df[signal_df["Signal"] == "SELL"]
    stops = signal_df[signal_df["Signal"] == "STOP"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("BUY Signals",  len(buys))
    c2.metric("SELL Signals", len(sells))
    c3.metric("ATR Stops",    len(stops))
    c4.metric("Total Signals", len(buys)+len(sells))

    if not buys.empty:
        st.markdown("### BUY Signal - Forward Return Analysis (5/10/20 bars)")
        rows = []
        for _, row in buys.iterrows():
            idx = int(row["t"])
            entry = plot_df.iloc[idx]["Close"]
            r5  = (plot_df.iloc[idx+5]["Close"]  - entry)/entry*100 if idx+5  < len(plot_df) else None
            r10 = (plot_df.iloc[idx+10]["Close"] - entry)/entry*100 if idx+10 < len(plot_df) else None
            r20 = (plot_df.iloc[idx+20]["Close"] - entry)/entry*100 if idx+20 < len(plot_df) else None
            rows.append({"Date": row["Date"].strftime("%Y-%m-%d"), "Strategy": row["Strategy"],
                         "Entry Rs": round(entry,2), "+5d %": round(r5,2) if r5 else None,
                         "+10d %": round(r10,2) if r10 else None, "+20d %": round(r20,2) if r20 else None})
        fwd_df = pd.DataFrame(rows).dropna()
        if not fwd_df.empty:
            pivot = fwd_df.groupby("Strategy")[["+5d %","+10d %","+20d %"]].mean().round(2)
            pivot["Win Rate (20d)"] = fwd_df.groupby("Strategy")["+20d %"].apply(lambda x: round((x>0).mean()*100,1))
            st.dataframe(pivot.style.background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)
        with st.expander("All BUY Signal Rows"):
            st.dataframe(fwd_df, use_container_width=True)

# 2D Chart
st.divider()
st.subheader("2D Signal Chart - Price + All Overlays")
fig2 = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.55,0.25,0.20],
    vertical_spacing=0.03, subplot_titles=["Price + Signals + EMA-200 + ATR Stop", z_label, "RSI (14)"])

fig2.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["Close"], mode="lines",
    line=dict(color="#4fc3f7", width=1.5), name="Close"), row=1, col=1)

if show_ema200:
    fig2.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["EMA200"], mode="lines",
        line=dict(color="#FFD700", width=2, dash="dot"), name="EMA-200"), row=1, col=1)

if show_atr_stop:
    fig2.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["ATRStop"], mode="lines",
        line=dict(color="#ff6b35", width=1.5, dash="dash"), name="ATR Stop"), row=1, col=1)

if show_fib:
    for label, price in fibs.items():
        if label in ["38.2%","61.8%","88.6%"]:
            clr = {"38.2%":"#4fc3f7","61.8%":"#00e5ff","88.6%":"#ff6090"}[label]
            fig2.add_hline(y=price, line_dash="dot", line_color=clr,
                annotation_text=f"Fib {label}", annotation_position="right", row=1, col=1)

if show_peaks and peaks:
    pk = plot_df.iloc[peaks]
    fig2.add_trace(go.Scatter(x=pk["Date"], y=pk["Close"], mode="markers",
        marker=dict(size=9, color="#ff4b6e", symbol="triangle-down"), name="Peak"), row=1, col=1)
if show_peaks and troughs:
    tr = plot_df.iloc[troughs]
    fig2.add_trace(go.Scatter(x=tr["Date"], y=tr["Close"], mode="markers",
        marker=dict(size=9, color="#00e676", symbol="triangle-up"), name="Trough"), row=1, col=1)

if show_signals and not signal_df.empty:
    for sig_type, color in [("BUY","#00ff88"),("SELL","#ff4b6e"),("STOP","#ff8800")]:
        sub = signal_df[signal_df["Signal"] == sig_type]
        if sub.empty: continue
        sym = "triangle-up" if sig_type == "BUY" else "triangle-down"
        fig2.add_trace(go.Scatter(x=sub["Date"], y=sub["Close"], mode="markers",
            marker=dict(size=12, color=color, symbol=sym, line=dict(width=1, color="white")),
            name=sig_type, text=sub["Strategy"],
            hovertemplate="<b>%{text}</b><br>Rs%{y:.2f}<br>%{x}<extra></extra>"), row=1, col=1)

fig2.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["Z"], mode="lines",
    line=dict(color="#b39ddb", width=1.5), name=z_label,
    fill="tozeroy", fillcolor="rgba(179,157,219,0.1)"), row=2, col=1)

fig2.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["RSI"], mode="lines",
    line=dict(color="#80cbc4", width=1.5), name="RSI"), row=3, col=1)
fig2.add_hline(y=70, line_dash="dash", line_color="red",   row=3, col=1)
fig2.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

fig2.update_layout(height=700, paper_bgcolor="#0a0e14", plot_bgcolor="#0d1117",
    font=dict(color="white"), margin=dict(l=0, r=0, t=40, b=0),
    legend=dict(bgcolor="rgba(10,14,20,0.8)", bordercolor="#2a3a5c", borderwidth=1))
fig2.update_xaxes(showgrid=True, gridcolor="#1a2035")
fig2.update_yaxes(showgrid=True, gridcolor="#1a2035")
st.plotly_chart(fig2, use_container_width=True)

# Nakshatra Summary
if show_nakshatra:
    st.divider()
    st.subheader("Nakshatra Signal Distribution")
    nak_counts  = plot_df["NakSignal"].value_counts()
    nak_returns = plot_df.groupby("NakSignal")["Returns"].mean()
    c1,c2,c3 = st.columns(3)
    for col, sig, emoji in [(c1,"BULL","BULL"),(c2,"NEUTRAL","NEUTRAL"),(c3,"BEAR","BEAR")]:
        col.metric(f"{emoji} Days", f"{nak_counts.get(sig,0)} days",
                   delta=f"Avg return: {nak_returns.get(sig,0):+.2f}%")

# Data Table
st.divider()
st.markdown("## Raw Data Table")
row_opt = st.selectbox("Rows to display", ["Last 10","Last 25","Last 50","Last 100","All Rows"], index=0)
rows_map = {"Last 10":10,"Last 25":25,"Last 50":50,"Last 100":100,"All Rows":None}
n = rows_map[row_opt]
display_cols = ["Date","Close","EMA200","ATRStop","RSI","NakSignal","NakName","Z","Returns"]
disp = plot_df[[c for c in display_cols if c in plot_df.columns]].copy()
disp["Date"] = disp["Date"].dt.strftime("%Y-%m-%d")
with st.expander("Show Data"):
    st.dataframe(disp.tail(n) if n else disp, use_container_width=True)
