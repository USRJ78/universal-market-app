import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

class CryptoStrategyHelper:
    def __init__(self):
        self.strategies = {
            "Discount Coin Strategy (DCS)": {
                "desc": "Buys major crypto assets when trading at a discount (below 50-day EMA) and UTBot trend is confirmed bullish. Exits on trend reversion or dynamic risk target."
            },
            "Chess Trading Strategy": {
                "desc": "Tactical system using 20-day channel breakouts for momentum expansion (Pawns) combined with a 2.5x ATR trailing-stop defense (Knights)."
            },
            "HFT Vector Bundle": {
                "desc": "Executes high-frequency swing trades using fast 5/15-day EMA crossovers filtered by RSI-14 oversold levels to exploit short-term volatility."
            },
            "Market Geometry Strategy": {
                "desc": "Buys pullback reversals at the 61.8% Fibonacci retracement level of the rolling 20-day high-low channel, targeting the rolling peak."
            },
            "Basket Selection Strategy (BSS)": {
                "desc": "Ranks the coin basket by 10-day rate-of-change momentum, dynamically holding the top leaders with trend confirmation and ATR trailing stops."
            },
            "Crypto Arbitrage": {
                "desc": "Statistical arbitrage spread-trading between the first two selected coins, executing long/short mean reversion trades on rolling 20-day spread Z-scores."
            }
        }

    def fetch_historical_prices(self, coins, start_date, end_date):
        """Downloads historical price data for the specified coins with warm-up buffer."""
        # Add 60 days buffer to compute ATR, RSI and EMAs cleanly before start_date
        buffer_start = start_date - timedelta(days=60)
        data = {}
        for coin in coins:
            ticker = f"{coin}-USD"
            try:
                df = yf.download(ticker, start=buffer_start, end=end_date)
                if not df.empty:
                    # Flatten MultiIndex columns if present
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df.index = pd.to_datetime(df.index).tz_localize(None)
                    data[coin] = df
            except Exception as e:
                print(f"Error downloading {ticker}: {e}")
        return data

    def compute_indicators(self, df, atr_period=10, ut_mult=1.0):
        """Calculates indicators used across strategies: ATR, RSI, EMAs, UTBot, High/Low."""
        df = df.copy()
        
        # 1. True Range & ATR
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        df["ATR10"] = tr.rolling(10).mean()
        df["ATR"] = tr.rolling(atr_period).mean()
        
        # 2. EMAs
        df["EMA5"] = df["Close"].ewm(span=5, adjust=False).mean()
        df["EMA15"] = df["Close"].ewm(span=15, adjust=False).mean()
        df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
        
        # 3. RSI-14
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df["RSI14"] = 100 - (100 / (1 + rs))
        
        # 4. Rolling 20-day High / Low
        df["High20"] = df["High"].rolling(20).max()
        df["Low20"] = df["Low"].rolling(20).min()
        
        # Shifted metrics to prevent lookahead bias in trading signals
        df["EMA5_prev"] = df["EMA5"].shift(1)
        df["EMA15_prev"] = df["EMA15"].shift(1)
        df["High20_prev"] = df["High20"].shift(1)
        df["Low20_prev"] = df["Low20"].shift(1)
        df["Fib618_prev"] = (df["High20_prev"] - 0.618 * (df["High20_prev"] - df["Low20_prev"]))
        
        # 5. UTBot Signal logic
        df["upper"] = df["Close"] - ut_mult * df["ATR"]
        df["lower"] = df["Close"] + ut_mult * df["ATR"]
        
        trend = []
        curr_trend = 1
        for i in range(len(df)):
            if i == 0:
                trend.append(curr_trend)
                continue
            close_val = df["Close"].iloc[i]
            prev_lower = df["lower"].iloc[i-1]
            prev_upper = df["upper"].iloc[i-1]
            
            if pd.isna(prev_lower) or pd.isna(prev_upper):
                trend.append(curr_trend)
                continue
                
            if close_val > prev_lower:
                curr_trend = 1
            elif close_val < prev_upper:
                curr_trend = -1
            trend.append(curr_trend)
            
        df["trend"] = trend
        df["trend_prev"] = df["trend"].shift(1)
        return df

    def run_single_asset_backtest(self, coin, df, start_date, initial_capital, fee_pct, slip_pct, entry_func, exit_func):
        """Executes a backtest loop on a single coin using custom signal functions."""
        # Filter to actual backtest timeframe (excluding warmup)
        bt_df = df.loc[df.index >= pd.to_datetime(start_date)].copy()
        if len(bt_df) < 2:
            empty_curve = pd.DataFrame(index=[pd.to_datetime(start_date)], data={"Equity": [initial_capital]})
            empty_curve.index.name = "Date"
            return empty_curve, pd.DataFrame()
            
        cash = initial_capital
        position = 0.0
        status = "CASH"
        entry_price = 0.0
        entry_date = None
        pos_entry_capital = 0.0
        max_price_since_entry = 0.0
        
        equity_curve = []
        trades = []
        
        for idx in range(len(bt_df)):
            current_date = bt_df.index[idx]
            row = bt_df.iloc[idx]
            close_price = float(row["Close"])
            
            if status == "IN_POSITION":
                max_price_since_entry = max(max_price_since_entry, close_price)
                
            # Check Exit Condition
            if status == "IN_POSITION" and exit_func(row, entry_price, max_price_since_entry, close_price):
                cash = position * close_price * (1.0 - fee_pct - slip_pct)
                pnl_raw = cash - pos_entry_capital
                pnl_pct = (pnl_raw / pos_entry_capital) * 100.0 if pos_entry_capital != 0 else 0.0
                
                # Exit Reason Resolution
                exit_reason = "Signal Exit"
                if close_price >= entry_price * 1.25:
                    exit_reason = "Take Profit (+25%)"
                elif close_price <= entry_price * 0.90:
                    exit_reason = "Stop Loss (-10%)"
                elif "ATR10" in row and close_price <= max_price_since_entry - 2.5 * row["ATR10"]:
                    exit_reason = "Trailing Stop"
                elif "Low20_prev" in row and close_price <= row["Low20_prev"]:
                    exit_reason = "Channel Exit"
                    
                trades.append({
                    "Stock": coin,
                    "Type": "SHORT EXIT" if exit_reason == "Signal Exit" else "SELL EXIT",
                    "Entry Date": entry_date,
                    "Exit Date": current_date,
                    "Entry Price": entry_price,
                    "Exit Price": close_price,
                    "Profit": pnl_raw,
                    "Return %": pnl_pct,
                    "Exit Reason": exit_reason
                })
                position = 0.0
                status = "CASH"
                
            # Check Entry Condition
            elif status == "CASH" and entry_func(row):
                pos_entry_capital = cash
                position = cash * (1.0 - fee_pct - slip_pct) / close_price
                cash = 0.0
                status = "IN_POSITION"
                entry_price = close_price
                entry_date = current_date
                max_price_since_entry = close_price
                
            # Record Equity
            if status == "IN_POSITION":
                daily_equity = position * close_price
            else:
                daily_equity = cash
                
            equity_curve.append({
                "Date": current_date,
                "Equity": daily_equity
            })
            
        # Unwind open position on final day
        if status == "IN_POSITION":
            final_date = bt_df.index[-1]
            final_close = float(bt_df["Close"].iloc[-1])
            final_cash = position * final_close * (1.0 - fee_pct - slip_pct)
            final_pnl = final_cash - pos_entry_capital
            final_pct = (final_pnl / pos_entry_capital) * 100.0 if pos_entry_capital != 0 else 0.0
            
            trades.append({
                "Stock": coin,
                "Type": "OPEN MTM",
                "Entry Date": entry_date,
                "Exit Date": final_date,
                "Entry Price": entry_price,
                "Exit Price": final_close,
                "Profit": final_pnl,
                "Return %": final_pct,
                "Exit Reason": "Open Position (MTM)"
            })
            # Overwrite final day equity with liquidated equity value
            equity_curve[-1]["Equity"] = final_cash
            
        equity_df = pd.DataFrame(equity_curve).set_index("Date")
        trades_df = pd.DataFrame(trades)
        
        return equity_df, trades_df

    def simulate_dcs(self, data, start_date, capital, fee_pct, slip_pct):
        """Simulates Discount Coin Strategy across selected coins (equal weight)."""
        equities = []
        all_trades = []
        cap_per_coin = capital / len(data) if data else capital
        
        for coin, df in data.items():
            entry_func = lambda row: row["Close"] < row["EMA50"] and row["trend"] == 1 and row["trend_prev"] == -1
            exit_func = lambda row, entry_p, max_p, close_p: row["trend"] == -1 or close_p >= entry_p * 1.25 or close_p <= entry_p * 0.90
            
            eq, tr = self.run_single_asset_backtest(coin, df, start_date, cap_per_coin, fee_pct, slip_pct, entry_func, exit_func)
            equities.append(eq)
            if not tr.empty:
                all_trades.append(tr)
                
        # Aggregate portfolio curves
        combined_equity = self.aggregate_equity_curves(equities, start_date, capital)
        combined_trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        return combined_equity, combined_trades

    def simulate_chess(self, data, start_date, capital, fee_pct, slip_pct):
        """Simulates Chess Trading Strategy (20-day Channel Breakout + 2.5x ATR stop)."""
        equities = []
        all_trades = []
        cap_per_coin = capital / len(data) if data else capital
        
        for coin, df in data.items():
            entry_func = lambda row: row["Close"] >= row["High20_prev"] and row["RSI14"] > 55
            exit_func = lambda row, entry_p, max_p, close_p: close_p <= max_p - 2.5 * row["ATR10"] or close_p <= row["Low20_prev"]
            
            eq, tr = self.run_single_asset_backtest(coin, df, start_date, cap_per_coin, fee_pct, slip_pct, entry_func, exit_func)
            equities.append(eq)
            if not tr.empty:
                all_trades.append(tr)
                
        combined_equity = self.aggregate_equity_curves(equities, start_date, capital)
        combined_trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        return combined_equity, combined_trades

    def simulate_hft(self, data, start_date, capital, fee_pct, slip_pct):
        """Simulates HFT Vector Bundle (5/15 EMA Crossover + RSI threshold)."""
        equities = []
        all_trades = []
        cap_per_coin = capital / len(data) if data else capital
        
        for coin, df in data.items():
            entry_func = lambda row: row["EMA5"] > row["EMA15"] and row["EMA5_prev"] <= row["EMA15_prev"] and row["RSI14"] < 65
            exit_func = lambda row, entry_p, max_p, close_p: row["EMA5"] < row["EMA15"] or row["RSI14"] > 75
            
            eq, tr = self.run_single_asset_backtest(coin, df, start_date, cap_per_coin, fee_pct, slip_pct, entry_func, exit_func)
            equities.append(eq)
            if not tr.empty:
                all_trades.append(tr)
                
        combined_equity = self.aggregate_equity_curves(equities, start_date, capital)
        combined_trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        return combined_equity, combined_trades

    def simulate_geometry(self, data, start_date, capital, fee_pct, slip_pct):
        """Simulates Market Geometry Strategy (61.8% Fib buy + 0/100 Channel exits)."""
        equities = []
        all_trades = []
        cap_per_coin = capital / len(data) if data else capital
        
        for coin, df in data.items():
            entry_func = lambda row: row["Close"] <= row["Fib618_prev"] and row["Close"] > row["Open"]
            exit_func = lambda row, entry_p, max_p, close_p: close_p >= row["High20_prev"] or close_p <= row["Low20_prev"]
            
            eq, tr = self.run_single_asset_backtest(coin, df, start_date, cap_per_coin, fee_pct, slip_pct, entry_func, exit_func)
            equities.append(eq)
            if not tr.empty:
                all_trades.append(tr)
                
        combined_equity = self.aggregate_equity_curves(equities, start_date, capital)
        combined_trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        return combined_equity, combined_trades

    def simulate_bss(self, data, start_date, capital, fee_pct, slip_pct):
        """Simulates Basket Selection Strategy (Dynamic Momentum Selection & Rebalancing)."""
        # Determine master calendar dates matching our dataset starting at start_date
        if not data:
            empty_curve = pd.DataFrame(index=[pd.to_datetime(start_date)], data={"Equity": [capital]})
            empty_curve.index.name = "Date"
            return empty_curve, pd.DataFrame()
            
        first_coin = list(data.keys())[0]
        bt_dates = data[first_coin].loc[data[first_coin].index >= pd.to_datetime(start_date)].index
        
        cash = capital
        positions = {}  # coin -> {qty, entry_price, peak_price, entry_date}
        
        # Max active coins based on basket size
        num_coins = len(data)
        K = 1 if num_coins <= 3 else 2
        
        equity_curve = []
        trades = []
        
        for current_date in bt_dates:
            # Calculate 10-day ROC for all coins on this date
            roc_vals = {}
            for coin, df in data.items():
                if current_date in df.index:
                    idx = df.index.get_loc(current_date)
                    if idx >= 10:
                        close_now = df["Close"].iloc[idx]
                        close_prev = df["Close"].iloc[idx-10]
                        roc_vals[coin] = (close_now / close_prev - 1.0) if close_prev > 0 else 0.0
            
            # Rank coins
            ranked_coins = [k for k, v in sorted(roc_vals.items(), key=lambda item: item[1], reverse=True)]
            top_ranked = ranked_coins[:K]
            
            # Calculate current total asset value
            total_assets_val = sum(positions[coin]["qty"] * float(data[coin].loc[current_date, "Close"]) for coin in positions)
            total_equity = cash + total_assets_val
            
            # Step 1: Manage Active Positions
            to_liquidate = []
            for coin in list(positions.keys()):
                close_price = float(data[coin].loc[current_date, "Close"])
                pos = positions[coin]
                pos["peak_price"] = max(pos["peak_price"], close_price)
                
                # Check ATR trailing stop
                atr10 = float(data[coin].loc[current_date, "ATR10"])
                trend = int(data[coin].loc[current_date, "trend"])
                
                stop_price = pos["peak_price"] - 2.0 * atr10
                
                if close_price <= stop_price or trend == -1:
                    to_liquidate.append(coin)
            
            # Process liquidations
            for coin in to_liquidate:
                close_price = float(data[coin].loc[current_date, "Close"])
                qty = positions[coin]["qty"]
                proceeds = qty * close_price * (1.0 - fee_pct - slip_pct)
                cash += proceeds
                
                pnl_raw = proceeds - positions[coin]["entry_cap"]
                pnl_pct = (pnl_raw / positions[coin]["entry_cap"]) * 100.0 if positions[coin]["entry_cap"] != 0 else 0.0
                
                exit_reason = "Momentum Drop" if int(data[coin].loc[current_date, "trend"]) == 1 else "Trend Shift (-1)"
                if close_price <= positions[coin]["peak_price"] - 2.0 * float(data[coin].loc[current_date, "ATR10"]):
                    exit_reason = "ATR Trailing Stop"
                    
                trades.append({
                    "Stock": coin,
                    "Type": "SELL EXIT",
                    "Entry Date": positions[coin]["entry_date"],
                    "Exit Date": current_date,
                    "Entry Price": positions[coin]["entry_price"],
                    "Exit Price": close_price,
                    "Profit": pnl_raw,
                    "Return %": pnl_pct,
                    "Exit Reason": exit_reason
                })
                del positions[coin]
                
            # Recalculate equity
            total_assets_val = sum(positions[coin]["qty"] * float(data[coin].loc[current_date, "Close"]) for coin in positions)
            total_equity = cash + total_assets_val
            
            # Step 2: Buy top-ranked leaders if slots open
            slots_available = K - len(positions)
            if slots_available > 0:
                capital_per_slot = total_equity / K
                for coin in top_ranked:
                    if coin not in positions and len(positions) < K:
                        close_price = float(data[coin].loc[current_date, "Close"])
                        trend = int(data[coin].loc[current_date, "trend"])
                        
                        # Only enter on bullish trend confirmation
                        if trend == 1:
                            buy_cap = min(cash, capital_per_slot)
                            if buy_cap > 10.0: # Minimum transaction size
                                qty = buy_cap * (1.0 - fee_pct - slip_pct) / close_price
                                cash -= buy_cap
                                positions[coin] = {
                                    "qty": qty,
                                    "entry_price": close_price,
                                    "peak_price": close_price,
                                    "entry_date": current_date,
                                    "entry_cap": buy_cap
                                }
                                
            # Re-record daily portfolio equity
            total_assets_val = sum(positions[coin]["qty"] * float(data[coin].loc[current_date, "Close"]) for coin in positions)
            total_equity = cash + total_assets_val
            
            equity_curve.append({
                "Date": current_date,
                "Equity": total_equity
            })
            
        # Final MTM liquidation for any remaining open positions
        if positions:
            final_date = bt_dates[-1]
            for coin, pos in positions.items():
                final_close = float(data[coin].loc[final_date, "Close"])
                proceeds = pos["qty"] * final_close * (1.0 - fee_pct - slip_pct)
                pnl_raw = proceeds - pos["entry_cap"]
                pnl_pct = (pnl_raw / pos["entry_cap"]) * 100.0 if pos["entry_cap"] != 0 else 0.0
                
                trades.append({
                    "Stock": coin,
                    "Type": "OPEN MTM",
                    "Entry Date": pos["entry_date"],
                    "Exit Date": final_date,
                    "Entry Price": pos["entry_price"],
                    "Exit Price": final_close,
                    "Profit": pnl_raw,
                    "Return %": pnl_pct,
                    "Exit Reason": "Open Position (MTM)"
                })
            # Final equity curve value liquidates everything
            final_equity = cash + sum(pos["qty"] * float(data[coin].loc[final_date, "Close"]) for coin, pos in positions.items())
            equity_curve[-1]["Equity"] = final_equity
            
        equity_df = pd.DataFrame(equity_curve).set_index("Date")
        trades_df = pd.DataFrame(trades)
        
        return equity_df, trades_df

    def simulate_arbitrage(self, data, start_date, capital, fee_pct, slip_pct):
        """Simulates statistical spread-trading arbitrage between the first two coins."""
        coins = list(data.keys())
        if len(coins) < 2:
            # Flat line return if insufficient assets
            dates = pd.date_range(start=start_date, end=datetime.now(), freq="D")
            empty_curve = pd.DataFrame(index=dates, data={"Equity": [capital]})
            empty_curve.index.name = "Date"
            return empty_curve, pd.DataFrame()
            
        coinA, coinB = coins[0], coins[1]
        
        # Align prices on dates using full data (including warm-up)
        fullA = data[coinA]
        fullB = data[coinB]
        
        merged = pd.merge(fullA[["Close"]].rename(columns={"Close": "A"}), 
                          fullB[["Close"]].rename(columns={"Close": "B"}), 
                          left_index=True, right_index=True, how="inner")
        
        if len(merged) < 5:
            dates = pd.date_range(start=start_date, end=datetime.now(), freq="D")
            empty_curve = pd.DataFrame(index=dates, data={"Equity": [capital]})
            empty_curve.index.name = "Date"
            return empty_curve, pd.DataFrame()
            
        merged["Ratio"] = merged["A"] / merged["B"]
        merged["Mean"] = merged["Ratio"].rolling(20).mean()
        merged["Std"] = merged["Ratio"].rolling(20).std()
        merged["ZScore"] = (merged["Ratio"] - merged["Mean"]) / (merged["Std"] + 1e-9)
        
        # Now filter to backtest range (>= start_date) and dropna
        merged = merged.loc[merged.index >= pd.to_datetime(start_date)].dropna().copy()
        
        if len(merged) < 2:
            dates = pd.date_range(start=start_date, end=datetime.now(), freq="D")
            empty_curve = pd.DataFrame(index=dates, data={"Equity": [capital]})
            empty_curve.index.name = "Date"
            return empty_curve, pd.DataFrame()
        
        cash = capital
        status = "CASH"  # CASH, LONG_SPREAD, SHORT_SPREAD
        entry_price_ratio = 0.0
        entry_price_A = 0.0
        entry_price_B = 0.0
        entry_date = None
        pos_entry_capital = 0.0
        
        equity_curve = []
        trades = []
        
        for idx in range(len(merged)):
            current_date = merged.index[idx]
            row = merged.iloc[idx]
            z = row["ZScore"]
            price_ratio = row["Ratio"]
            closeA = float(row["A"])
            closeB = float(row["B"])
            
            # Check exit
            if status == "LONG_SPREAD" and (z >= 0.0 or z <= -3.5):
                # Unwind spread: Long A, Short B
                pnl_A = (closeA / entry_price_A - 1.0) * (pos_entry_capital * 0.5)
                pnl_B = -1.0 * (closeB / entry_price_B - 1.0) * (pos_entry_capital * 0.5)
                pnl_raw = (pnl_A + pnl_B) - (pos_entry_capital * (fee_pct + slip_pct) * 2.0)
                cash = pos_entry_capital + pnl_raw
                pnl_pct = (pnl_raw / pos_entry_capital) * 100.0 if pos_entry_capital != 0 else 0.0
                
                exit_reason = "Spread Convergence" if z >= 0.0 else "Spread Stop Loss"
                trades.append({
                    "Stock": f"{coinA}/{coinB} Spread",
                    "Type": "SPREAD EXIT",
                    "Entry Date": entry_date,
                    "Exit Date": current_date,
                    "Entry Price": entry_price_ratio,
                    "Exit Price": price_ratio,
                    "Profit": pnl_raw,
                    "Return %": pnl_pct,
                    "Exit Reason": exit_reason
                })
                status = "CASH"
                
            elif status == "SHORT_SPREAD" and (z <= 0.0 or z >= 3.5):
                # Unwind spread: Short A, Long B
                pnl_A = -1.0 * (closeA / entry_price_A - 1.0) * (pos_entry_capital * 0.5)
                pnl_B = (closeB / entry_price_B - 1.0) * (pos_entry_capital * 0.5)
                pnl_raw = (pnl_A + pnl_B) - (pos_entry_capital * (fee_pct + slip_pct) * 2.0)
                cash = pos_entry_capital + pnl_raw
                pnl_pct = (pnl_raw / pos_entry_capital) * 100.0 if pos_entry_capital != 0 else 0.0
                
                exit_reason = "Spread Convergence" if z <= 0.0 else "Spread Stop Loss"
                trades.append({
                    "Stock": f"{coinA}/{coinB} Spread",
                    "Type": "SPREAD EXIT",
                    "Entry Date": entry_date,
                    "Exit Date": current_date,
                    "Entry Price": entry_price_ratio,
                    "Exit Price": price_ratio,
                    "Profit": pnl_raw,
                    "Return %": pnl_pct,
                    "Exit Reason": exit_reason
                })
                status = "CASH"
                
            # Check entry
            elif status == "CASH" and z < -2.0:
                # Enter Long Spread: Long A, Short B
                pos_entry_capital = cash
                cash = 0.0
                status = "LONG_SPREAD"
                entry_price_ratio = price_ratio
                entry_price_A = closeA
                entry_price_B = closeB
                entry_date = current_date
                
            elif status == "CASH" and z > 2.0:
                # Enter Short Spread: Short A, Long B
                pos_entry_capital = cash
                cash = 0.0
                status = "SHORT_SPREAD"
                entry_price_ratio = price_ratio
                entry_price_A = closeA
                entry_price_B = closeB
                entry_date = current_date
                
            # Record Equity
            if status == "LONG_SPREAD":
                pnl_A = (closeA / entry_price_A - 1.0) * (pos_entry_capital * 0.5)
                pnl_B = -1.0 * (closeB / entry_price_B - 1.0) * (pos_entry_capital * 0.5)
                daily_equity = pos_entry_capital + pnl_A + pnl_B - (pos_entry_capital * (fee_pct + slip_pct))
            elif status == "SHORT_SPREAD":
                pnl_A = -1.0 * (closeA / entry_price_A - 1.0) * (pos_entry_capital * 0.5)
                pnl_B = (closeB / entry_price_B - 1.0) * (pos_entry_capital * 0.5)
                daily_equity = pos_entry_capital + pnl_A + pnl_B - (pos_entry_capital * (fee_pct + slip_pct))
            else:
                daily_equity = cash
                
            equity_curve.append({
                "Date": current_date,
                "Equity": daily_equity
            })
            
        # Final MTM liquidation
        if status != "CASH":
            final_date = merged.index[-1]
            final_row = merged.iloc[-1]
            closeA = float(final_row["A"])
            closeB = float(final_row["B"])
            price_ratio = final_row["Ratio"]
            
            if status == "LONG_SPREAD":
                pnl_A = (closeA / entry_price_A - 1.0) * (pos_entry_capital * 0.5)
                pnl_B = -1.0 * (closeB / entry_price_B - 1.0) * (pos_entry_capital * 0.5)
            else:
                pnl_A = -1.0 * (closeA / entry_price_A - 1.0) * (pos_entry_capital * 0.5)
                pnl_B = (closeB / entry_price_B - 1.0) * (pos_entry_capital * 0.5)
                
            pnl_raw = (pnl_A + pnl_B) - (pos_entry_capital * (fee_pct + slip_pct) * 2.0)
            final_cash = pos_entry_capital + pnl_raw
            pnl_pct = (pnl_raw / pos_entry_capital) * 100.0 if pos_entry_capital != 0 else 0.0
            
            trades.append({
                "Stock": f"{coinA}/{coinB} Spread",
                "Type": "OPEN MTM",
                "Entry Date": entry_date,
                "Exit Date": final_date,
                "Entry Price": entry_price_ratio,
                "Exit Price": price_ratio,
                "Profit": pnl_raw,
                "Return %": pnl_pct,
                "Exit Reason": "Open Position (MTM)"
            })
            equity_curve[-1]["Equity"] = final_cash
            
        if not equity_curve:
            dates = pd.date_range(start=start_date, end=datetime.now(), freq="D")
            empty_curve = pd.DataFrame(index=dates, data={"Equity": [capital]})
            empty_curve.index.name = "Date"
            return empty_curve, pd.DataFrame()
            
        equity_df = pd.DataFrame(equity_curve).set_index("Date")
        trades_df = pd.DataFrame(trades)
        
        return equity_df, trades_df

    def aggregate_equity_curves(self, curves_list, start_date, total_capital):
        """Merges and averages equity curves across assets, filling index gaps cleanly."""
        if not curves_list:
            dates = pd.date_range(start=start_date, end=datetime.now(), freq="D")
            return pd.DataFrame(index=dates, data={"Equity": [total_capital]})
            
        # Re-index all curves to match consecutive calendar dates
        min_date = min(c.index.min() for c in curves_list)
        max_date = max(c.index.max() for c in curves_list)
        master_index = pd.date_range(start=min_date, end=max_date, freq="D")
        
        aligned_equities = []
        for c in curves_list:
            c_aligned = c.reindex(master_index).ffill().fillna(total_capital / len(curves_list))
            aligned_equities.append(c_aligned["Equity"])
            
        combined = pd.DataFrame(aligned_equities).T.sum(axis=1)
        res = pd.DataFrame(combined, columns=["Equity"])
        res.index.name = "Date"
        # Filter to target start_date
        res = res.loc[res.index >= pd.to_datetime(start_date)]
        return res

    def calculate_metrics(self, df_equity, initial_capital):
        """Calculates performance risk parameters for a given equity series (365-day crypto cycles)."""
        if df_equity.empty or len(df_equity) < 2:
            return {
                "CAGR": 0.0,
                "Sharpe": 0.0,
                "Max_DD": 0.0,
                "Total_Return": 0.0,
                "Ending_Capital": initial_capital
            }
            
        equity = df_equity["Equity"].values
        dates = df_equity.index.values
        
        total_return = (equity[-1] / equity[0] - 1.0) * 100.0
        
        # CAGR (using actual calendar days for crypto)
        days = (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days
        years = days / 365.25
        if years > 0:
            cagr = ((equity[-1] / equity[0]) ** (1.0 / years) - 1.0) * 100.0
        else:
            cagr = 0.0
            
        # Sharpe (annualized with 365 days)
        daily_returns = df_equity["Equity"].pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() != 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
        else:
            sharpe = 0.0
            
        # Max Drawdown
        peak = np.maximum.accumulate(equity)
        drawdowns = (equity - peak) / peak * 100.0
        max_dd = drawdowns.min()
        
        return {
            "CAGR": cagr,
            "Sharpe": sharpe,
            "Max_DD": max_dd,
            "Total_Return": total_return,
            "Ending_Capital": equity[-1]
        }

    def get_aligned_strategy_returns(self, sim_results):
        """Aligns daily strategy returns into a single multi-column DataFrame."""
        aligned_df = None
        for name, (curve, _) in sim_results.items():
            if curve.empty:
                continue
            curve = curve.copy()
            curve["Return"] = curve["Equity"].pct_change().fillna(0.0)
            strat_df = curve[["Equity", "Return"]].rename(
                columns={"Equity": f"{name}_Equity", "Return": f"{name}_Return"}
            )
            if aligned_df is None:
                aligned_df = strat_df
            else:
                aligned_df = pd.merge(aligned_df, strat_df, left_index=True, right_index=True, how="outer")
                
        if aligned_df is not None:
            aligned_df = aligned_df.sort_index().ffill().fillna(0.0)
            aligned_df = aligned_df.reset_index()
            # Ensure Date column is standard datetime timezone-naive
            aligned_df["Date"] = pd.to_datetime(aligned_df["Date"]).dt.normalize()
        return aligned_df
