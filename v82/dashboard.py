import streamlit as st
import sqlite3
import pandas as pd

# -------------------------------
# CONFIG (MATCH ENGINE)
# -------------------------------
TOTAL_CAPITAL = 700000

st.set_page_config(layout="wide")
st.title("Polymarket V8.4 Capital Dashboard")

con = sqlite3.connect("meta.db")

# -------------------------------
# LOAD DATA
# -------------------------------
open_tr = pd.read_sql("select * from trades where status='OPEN'", con)
closed = pd.read_sql("select * from trades where status='CLOSED'", con)
portfolio = pd.read_sql("select * from portfolio order by id", con)

# -------------------------------
# CALCULATIONS
# -------------------------------
closed_pnl = closed["pnl_value"].sum() if len(closed) > 0 else 0
open_pnl = open_tr["pnl_value"].sum() if len(open_tr) > 0 else 0

total_pnl = closed_pnl + open_pnl
equity = TOTAL_CAPITAL + total_pnl

# -------------------------------
# METRICS
# -------------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Closed PnL (₹)", round(closed_pnl, 2))
col2.metric("Open PnL (₹)", round(open_pnl, 2))
col3.metric("Total Equity (₹)", round(equity, 2))

# -------------------------------
# EQUITY CURVE
# -------------------------------
st.subheader("Equity Curve")

if len(portfolio) > 0:
    # normalize properly
    portfolio["equity"] = portfolio["equity"].fillna(TOTAL_CAPITAL)
    st.line_chart(portfolio["equity"])
else:
    st.info("No equity data yet. Let engine run for a few cycles.")

# -------------------------------
# OPEN TRADES
# -------------------------------
st.subheader("Open Trades")

if len(open_tr) > 0:
    st.dataframe(open_tr, use_container_width=True)
else:
    st.info("No open trades")

# -------------------------------
# CLOSED TRADES
# -------------------------------
st.subheader("Closed Trades")

if len(closed) > 0:
    st.dataframe(closed, use_container_width=True)
else:
    st.info("No closed trades yet")

# -------------------------------
# SUMMARY
# -------------------------------
st.subheader("Portfolio Summary")

st.write(f"Total Capital: ₹{TOTAL_CAPITAL}")
st.write(f"Total PnL: ₹{round(total_pnl,2)}")
st.write(f"Return %: {round((total_pnl / TOTAL_CAPITAL)*100,2)}%")