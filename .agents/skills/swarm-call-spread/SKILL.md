---
name: swarm-call-spread
description: Multi-Agent Swarm Bot Driven 1x2 Ratio Call Spread Strategy for Indian Equities and Crypto Options. Triggers on 52-week momentum, volatility squeeze, and Black-Scholes zero net debit 1x2 ratio call spreads.
---

# 🐝 MULTI-AGENT SWARM BOT DRIVEN 1X2 CALL SPREAD SKILL

## 📌 Overview
This Antigravity Skill equips the agent to execute, backtest, and scan market breakouts using the **Multi-Agent Swarm 1x2 Ratio Call Spread Strategy**.

---

## 📐 Core Architecture & Parameters

### 1. Sub-Agent Swarm
- **Agent Alpha (Momentum)**: Triggers when price is within 2% of 52-week high ($S \ge 0.98 \times H_{52}$) and EMA 20 > EMA 50.
- **Agent Beta (Vol Squeeze)**: Triggers when 10-day ATR compresses relative to 50-day ATR ($\text{ATR}_{10} / \text{ATR}_{50} < 0.92$).
- **Agent Gamma (Option Geometry)**: Solves Black-Scholes strike matrices for **Zero Net Debit 1x2 Ratio Call Spreads**:
  - **Buy 1x ATM Call ($K_1$)**
  - **Sell 2x OTM Call ($K_2 \approx K_1 \times 1.045$)**
- **Agent Delta (Swarm Overseer)**: Enforces Swarm Conviction Score $\ge 70\%$ and fixed 8% risk allocation per trade.

---

## 🛠️ Included Executable Engines

- **Master Bundle Script**: `analysis/SWARM_CALL_SPREAD_MASTER_BUNDLE.py`
- **10-Year Backtest Engine**: `analysis/swarm_call_spread_10yr_backtest.py`
- **Groww API Stock Executor**: `analysis/groww_stock_master_trader.py`
- **Delta API Options Bot**: `analysis/live_swarm_utbot_master_bot.py`

---

## 🚀 Execution Instructions for Antigravity Agent
To run a market scan or backtest using this skill:
1. Run `python analysis/SWARM_CALL_SPREAD_MASTER_BUNDLE.py` to trigger full 10-year backtest and live market scan.
2. For Groww API paper-trading, execute `python analysis/groww_stock_master_trader.py`.
