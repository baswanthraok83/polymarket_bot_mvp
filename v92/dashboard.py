import streamlit as st
import sqlite3
import pandas as pd
import numpy as np

TOTAL_CAPITAL = 700000

st.set_page_config(layout="wide")
st.title("Polymarket Smart Dashboard V3")

# =========================
# DB
# =========================
con = sqlite3.connect("trades.db")

# =========================
# LOAD DATA
# =========================
closed = pd.read_sql("""
                     SELECT * FROM trades WHERE status='CLOSED'
                     """, con)

open_tr = pd.read_sql("""
                      SELECT * FROM trades WHERE status='OPEN'
                      """, con)

# =========================
# CLEAN
# =========================
for df in [open_tr, closed]:
    if len(df):
        df["pnl_value"] = pd.to_numeric(df["pnl_value"], errors="coerce").fillna(0)
        df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors="coerce").fillna(0)
        df["stake"] = pd.to_numeric(df["stake"], errors="coerce").fillna(0)

        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

# =========================
# CORE METRICS
# =========================
closed_pnl = closed["pnl_value"].sum() if len(closed) else 0
open_pnl = open_tr["pnl_value"].sum() if len(open_tr) else 0
total_pnl = closed_pnl + open_pnl

equity = TOTAL_CAPITAL + total_pnl
capital_deployed = open_tr["stake"].sum() if len(open_tr) else 0

deployment_pct = (capital_deployed / TOTAL_CAPITAL) * 100 if TOTAL_CAPITAL else 0

# =========================
# TOP METRICS
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Closed PnL (₹)", round(closed_pnl, 2))
c2.metric("Open PnL (₹)", round(open_pnl, 2))
c3.metric("Total Equity (₹)", round(equity, 2))
c4.metric("Capital Deployed (₹)", round(capital_deployed, 2))

st.progress(min(deployment_pct / 100, 1.0))
st.caption(f"Deployment: {round(deployment_pct,2)}% of capital")

# =========================
# OPEN TRADES
# =========================
st.subheader("Open Trades")

if len(open_tr):

    now = pd.Timestamp.utcnow()
    open_tr["duration_min"] = (now - open_tr["ts"]).dt.total_seconds() / 60

    display_open = open_tr.drop(columns=["token_id"], errors="ignore")

    st.dataframe(display_open, use_container_width=True)

else:
    st.info("No open trades")

# =========================
# CLOSED TRADES
# =========================
st.subheader("Closed Trades")

if len(closed):
    display_closed = closed.drop(columns=["token_id"], errors="ignore")
    st.dataframe(display_closed, use_container_width=True)
else:
    st.info("No closed trades")

# =========================
# STRATEGY PERFORMANCE
# =========================
st.subheader("Strategy Performance (Closed Trades)")

if len(closed):
    strat_perf = closed.groupby("strategy")["pnl_value"].sum().sort_values(ascending=False)
    st.bar_chart(strat_perf)
else:
    st.info("No closed trades")

# =========================
# EXPECTANCY
# =========================
st.subheader("Expectancy")

if len(closed):
    wins = closed[closed["pnl_value"] > 0]
    losses = closed[closed["pnl_value"] < 0]

    win_rate = len(wins) / len(closed) if len(closed) else 0
    avg_win = wins["pnl_value"].mean() if len(wins) else 0
    avg_loss = losses["pnl_value"].mean() if len(losses) else 0

    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    st.metric("Expectancy per Trade (₹)", round(expectancy, 2))
else:
    st.info("Not enough data")

# =========================
# SUMMARY
# =========================
st.subheader("Portfolio Summary")

st.write(f"Total Capital: ₹{TOTAL_CAPITAL}")
st.write(f"Capital Deployed: ₹{round(capital_deployed,2)}")
st.write(f"Total PnL: ₹{round(total_pnl,2)}")
st.write(f"Return %: {round((total_pnl / TOTAL_CAPITAL)*100,2)}%")