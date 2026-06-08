
import streamlit as st, sqlite3, pandas as pd
from modules.db import init_db
init_db()
st.set_page_config(page_title="V6.6 Unified", layout="wide")
st.title("Polymarket V6.6 Unified Stable Edition")
con=sqlite3.connect("portfolio.db")
df=pd.read_sql_query("select * from trades order by id desc", con)
tabs=st.tabs(["Open Trades","Analytics","AI Insights"])
with tabs[0]:
    st.dataframe(df, use_container_width=True)
with tabs[1]:
    if not df.empty:
        st.metric("Trades", len(df))
        st.line_chart(df["pnl"])
with tabs[2]:
    st.write("System healthy. Focus on high liquidity markets.")
