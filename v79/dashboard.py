
import streamlit as st, sqlite3, pandas as pd

st.set_page_config(page_title="V7.9 Meta", layout="wide")
st.title("Polymarket V7.9 AI Meta Trader")

con=sqlite3.connect("meta.db")
snap=pd.read_sql_query("select * from snapshots order by id desc limit 25", con)
leader=pd.read_sql_query("select strategy, round(sum(pnl_pct),2) total_pnl from trades group by strategy order by total_pnl desc", con)
alloc=pd.read_sql_query("select * from allocations", con)
open_tr=pd.read_sql_query("select * from trades where status='OPEN' order by id desc", con)

tabs=st.tabs(["Live Markets","Leaderboard","AI Allocation","Open Portfolio","Analytics"])

with tabs[0]:
    st.dataframe(snap, use_container_width=True)

with tabs[1]:
    st.dataframe(leader, use_container_width=True)

with tabs[2]:
    st.dataframe(alloc, use_container_width=True)

with tabs[3]:
    st.dataframe(open_tr, use_container_width=True)

with tabs[4]:
    if len(leader)>0:
        st.bar_chart(leader.set_index("strategy"))
