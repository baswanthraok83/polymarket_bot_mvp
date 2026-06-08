
import streamlit as st, sqlite3, pandas as pd
st.set_page_config(page_title="V6", layout="wide")
st.title("Polymarket V6 Simulator")
con=sqlite3.connect("portfolio.db")
df=pd.read_sql_query("select * from trades order by id desc", con)
st.metric("Trades", len(df))
if not df.empty:
    st.line_chart(df["pnl"])
st.dataframe(df, use_container_width=True)
