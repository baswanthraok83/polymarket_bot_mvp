
import streamlit as st, sqlite3, pandas as pd

st.set_page_config(page_title="V7.7", layout="wide")
st.title("Polymarket V7.7 Auto Paper Trader")

con=sqlite3.connect("portfolio.db")
snap=pd.read_sql_query("select * from snapshots order by id desc limit 25", con)
open_tr=pd.read_sql_query("select * from paper_trades where status='OPEN' order by id desc", con)
closed=pd.read_sql_query("select * from paper_trades where status='CLOSED' order by id desc", con)

tabs=st.tabs(["Live Markets","Open Trades","Closed Trades","Analytics"])

with tabs[0]:
    st.dataframe(snap, use_container_width=True)

with tabs[1]:
    st.dataframe(open_tr, use_container_width=True)

with tabs[2]:
    st.dataframe(closed, use_container_width=True)

with tabs[3]:
    total=len(closed)
    wins=len(closed[closed["pnl_pct"]>0]) if total>0 else 0
    wr=(wins/total*100) if total>0 else 0
    st.metric("Closed Trades", total)
    st.metric("Win Rate %", round(wr,2))
    if len(closed)>0:
        st.line_chart(closed["pnl_pct"])
