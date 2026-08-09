import numpy as np
import pandas as pd
import yfinance as yf
import requests
from scipy.stats import norm
from datetime import datetime
import time


# -------------------------------
# BLACK SCHOLES
# -------------------------------
def black_scholes_price(S, K, T, r, sigma, option_type="call"):
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0

    d1 = (
        np.log(S / K) + (r + 0.5 * sigma ** 2) * T
    ) / (sigma * np.sqrt(T))

    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return max(price, 0)


# -------------------------------
# RISK FREE RATE
# -------------------------------
def get_risk_free_rate():
    try:
        bond = yf.download("^INDI10Y", period="5d", progress=False)
        rate = float(bond["Close"].iloc[-1]) / 100
        return rate
    except:
        return 0.07


# -------------------------------
# GRAHAM VALUE
# -------------------------------
def graham_intrinsic_value(ticker, growth_method="auto"):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        eps = info.get("trailingEps")
        roe = info.get("returnOnEquity")
        payout = info.get("payoutRatio", 0)

        if eps is None:
            return None

        growth = None

        if growth_method in ["auto", "eps_cagr"]:
            try:
                earnings = stock.earnings
                if len(earnings) >= 5:
                    first = earnings["Earnings"].iloc[0]
                    last = earnings["Earnings"].iloc[-1]
                    years = len(earnings) - 1
                    growth = ((last / first) ** (1 / years) - 1) * 100
            except:
                growth = None

        if growth is None:
            if roe is not None:
                retention = 1 - payout
                growth = roe * retention * 100
            else:
                growth = 5

        growth = min(growth, 20)

        intrinsic = eps * (8.5 + 2 * growth)
        return intrinsic

    except:
        return None


# -------------------------------
# NSE OPTION CHAIN
# -------------------------------
def fetch_option_chain(symbol):
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(1)

        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        data = session.get(url, headers=headers, timeout=10).json()

        return data

    except:
        return None


# -------------------------------
# FIND BEST OPTION
# -------------------------------
def find_best_option(symbol, capital):
    data = fetch_option_chain(symbol)

    if data is None:
        return None

    r = get_risk_free_rate()
    best_trade = None
    best_edge = 0

    records = data["records"]["data"]

    for row in records:
        strike = row["strikePrice"]

        for opt_type_key in ["CE", "PE"]:
            if opt_type_key not in row:
                continue

            opt = row[opt_type_key]

            market_price = opt.get("lastPrice")
            iv = opt.get("impliedVolatility")
            lot_size = opt.get("marketLot", 1)

            if not market_price or not iv:
                continue

            expiry = pd.to_datetime(opt["expiryDate"])
            days = (expiry - pd.Timestamp.today()).days

            if days <= 0:
                continue

            T = days / 365
            sigma = iv / 100

            S = data["records"]["underlyingValue"]

            option_type = "call" if opt_type_key == "CE" else "put"

            theoretical = black_scholes_price(
                S, strike, T, r, sigma, option_type
            )

            edge = theoretical - market_price

            if edge > best_edge:
                max_allocation = capital * 0.10
                cost_per_lot = market_price * lot_size
                lots = int(max_allocation // cost_per_lot)

                if lots < 1:
                    continue

                best_edge = edge

                best_trade = {
                    "symbol": symbol,
                    "type": option_type,
                    "strike": strike,
                    "expiry": expiry,
                    "market_price": market_price,
                    "theoretical_price": theoretical,
                    "edge": edge,
                    "lot_size": lot_size,
                    "lots": lots,
                    "capital_used": lots * cost_per_lot
                }

    return best_trade


# -------------------------------
# MONTE CARLO
# -------------------------------
def monte_carlo_simulation(
    initial_capital,
    expected_return,
    volatility,
    simulations=1000,
    days=30
):
    results = []

    for _ in range(simulations):
        capital = initial_capital

        for _ in range(days):
            daily_return = np.random.normal(
                expected_return / 252,
                volatility / np.sqrt(252)
            )

            capital *= (1 + daily_return)

        results.append(capital)

    results = np.array(results)

    summary = {
        "worst_case": np.percentile(results, 5),
        "expected_case": np.mean(results),
        "best_case": np.percentile(results, 95),
        "loss_probability": np.mean(results < initial_capital)
    }

    return results, summary


# -------------------------------
# SCAN ALL STOCKS
# -------------------------------
def scan_market(tickers, capital):
    trades = []

    for ticker in tickers:
        try:
            intrinsic = graham_intrinsic_value(ticker)

            if intrinsic is None:
                continue

            stock = yf.Ticker(ticker)
            price = stock.history(period="5d")["Close"].iloc[-1]

            if price >= intrinsic:
                continue

            symbol = ticker.replace(".NS", "")
            trade = find_best_option(symbol, capital)

            if trade:
                trade["intrinsic"] = intrinsic
                trade["spot_price"] = price
                trades.append(trade)

        except:
            continue

    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)
    df = df.sort_values("edge", ascending=False)

    return df