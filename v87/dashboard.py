import streamlit as st
import sqlite3
import pandas as pd

TOTAL_CAPITAL = 700000

st.set_page_config(layout="wide")
st.title("Polymarket V8.5 Smart Dashboard")

con = sqlite3.connect("meta.db")

# -------------------------------
# LOAD DATA
# -------------------------------
open_tr = pd.read_sql("select * from trades where status='OPEN'", con)
closed = pd.read_sql("select * from trades where status='CLOSED'", con)
portfolio = pd.read_sql("select * from portfolio order by id", con)

# -------------------------------
# 🔥 FIX: CLEAN NUMERIC COLUMNS
# -------------------------------
for df in [open_tr, closed]:
    if len(df) > 0:
        df["pnl_value"] = pd.to_numeric(df["pnl_value"], errors="coerce").fillna(0)
        df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors="coerce").fillna(0)

# -------------------------------
# CALCULATIONS
# -------------------------------
closed_pnl = closed["pnl_value"].sum() if len(closed) else 0
open_pnl = open_tr["pnl_value"].sum() if len(open_tr) else 0

total_pnl = closed_pnl + open_pnl
equity = TOTAL_CAPITAL + total_pnl

total_trades = len(open_tr) + len(closed)
closed_trades = len(closed)
open_trades = len(open_tr)

# -------------------------------
# WIN / LOSS LOGIC (FIXED)
# -------------------------------
wins = closed[closed["pnl_value"] > 0]
losses = closed[closed["pnl_value"] < 0]

win_rate = (len(wins) / closed_trades * 100) if closed_trades else 0

avg_win = wins["pnl_value"].mean() if len(wins) else 0
avg_loss = losses["pnl_value"].mean() if len(losses) else 0

max_win = wins["pnl_value"].max() if len(wins) else 0
max_loss = losses["pnl_value"].min() if len(losses) else 0

# -------------------------------
# TOP METRICS
# -------------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Closed PnL (₹)", round(closed_pnl, 2))
col2.metric("Open PnL (₹)", round(open_pnl, 2))
col3.metric("Total Equity (₹)", round(equity, 2))

# -------------------------------
# TRADE STATS
# -------------------------------
st.subheader("Trade Statistics")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Trades", total_trades)
c2.metric("Open Trades", open_trades)
c3.metric("Closed Trades", closed_trades)
c4.metric("Win Rate (%)", round(win_rate, 2))

# -------------------------------
# PERFORMANCE
# -------------------------------
st.subheader("Performance Breakdown")

p1, p2, p3, p4 = st.columns(4)

p1.metric("Avg Win (₹)", round(avg_win, 2))
p2.metric("Avg Loss (₹)", round(avg_loss, 2))
p3.metric("Max Win (₹)", round(max_win, 2))
p4.metric("Max Loss (₹)", round(max_loss, 2))

# -------------------------------
# EQUITY CURVE
# -------------------------------
st.subheader("Equity Curve")

if len(portfolio):
    portfolio["equity"] = pd.to_numeric(portfolio["equity"], errors="coerce").fillna(TOTAL_CAPITAL)
    st.line_chart(portfolio["equity"])
else:
    st.info("No equity data yet")

# -------------------------------
# OPEN TRADES
# -------------------------------
st.subheader("Open Trades")

if len(open_tr):
    st.dataframe(open_tr, use_container_width=True)
else:
    st.info("No open trades")

# -------------------------------
# CLOSED TRADES
# -------------------------------
st.subheader("Closed Trades")

if len(closed):
    st.dataframe(closed, use_container_width=True)
else:
    st.info("No closed trades")

# -------------------------------
# SUMMARY
# -------------------------------
st.subheader("Portfolio Summary")

st.write(f"Total Capital: ₹{TOTAL_CAPITAL}")
st.write(f"Total PnL: ₹{round(total_pnl,2)}")
st.write(f"Return %: {round((total_pnl / TOTAL_CAPITAL)*100,2)}%")