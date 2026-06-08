import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Polymarket Scanner", layout="wide")
st.title("Polymarket Real Data Scanner")

con = sqlite3.connect("portfolio.db")

tabs = st.tabs(["Live Markets", "Top Movers"])

# ---------------- LIVE TAB ----------------
with tabs[0]:
    latest = pd.read_sql_query("""
                               SELECT *
                               FROM snapshots
                               WHERE ts = (SELECT MAX(ts) FROM snapshots)
                               """, con)

    st.subheader("Current Snapshot")
    st.dataframe(latest, use_container_width=True)

# ---------------- MOVERS TAB ----------------
with tabs[1]:

    times = pd.read_sql_query("""
                              SELECT DISTINCT ts
                              FROM snapshots
                              ORDER BY ts DESC
                                  LIMIT 2
                              """, con)

    if len(times) < 2:
        st.warning("Need 2 snapshot cycles.")
    else:
        latest_ts = times.iloc[0]["ts"]
        prev_ts   = times.iloc[1]["ts"]

        curr = pd.read_sql_query(
            f"SELECT market, yes_price FROM snapshots WHERE ts='{latest_ts}'",
            con
        )

        prev = pd.read_sql_query(
            f"SELECT market, yes_price FROM snapshots WHERE ts='{prev_ts}'",
            con
        )

        df = curr.merge(prev, on="market", suffixes=("_curr", "_prev"))

        df["Change %"] = ((df["yes_price_curr"] - df["yes_price_prev"]) /
                          df["yes_price_prev"]) * 100

        df = df.rename(columns={
            "yes_price_prev":"Prev YES",
            "yes_price_curr":"Curr YES"
        })

        df = df[["market", "Prev YES", "Curr YES", "Change %"]]
        df = df.sort_values("Change %", ascending=False)

        st.dataframe(df, use_container_width=True)