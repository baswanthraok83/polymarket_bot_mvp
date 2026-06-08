
import streamlit as st, sqlite3, pandas as pd

st.set_page_config(page_title="V7.8 Arena", layout="wide")
st.title("Polymarket V7.8 Strategy Arena")

con=sqlite3.connect("arena.db")
snap=pd.read_sql_query("select * from snapshots order by id desc limit 25", con)
open_tr=pd.read_sql_query("select * from trades where status='OPEN' order by id desc", con)
closed=pd.read_sql_query("select * from trades where status='CLOSED' order by id desc", con)
leader=pd.read_sql_query("select strategy, round(sum(pnl_pct),2) as total_pnl from trades group by strategy order by total_pnl desc", con)

tabs=st.tabs(["Live Markets","Leaderboard","Open Trades","Closed Trades","Analytics"])

with tabs[0]:
    st.dataframe(snap, use_container_width=True)

with tabs[1]:
    st.dataframe(leader, use_container_width=True)

with tabs[2]:
    st.dataframe(open_tr, use_container_width=True)

with tabs[3]:
    st.dataframe(closed, use_container_width=True)

with tabs[4]:
    st.metric("Total Trades", len(open_tr)+len(closed))
    if len(leader)>0:
        st.bar_chart(leader.set_index("strategy"))
