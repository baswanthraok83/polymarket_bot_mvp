
import streamlit as st, pandas as pd, sqlite3
st.set_page_config(page_title="V5.1", layout="wide")
st.title("Polymarket V5.1 Dashboard")
con=sqlite3.connect("portfolio.db")
df=pd.read_sql_query("select * from trades order by id desc", con)
st.metric("Total Trades", len(df))
if not df.empty:
    st.line_chart(df["pnl"])
st.dataframe(df, use_container_width=True)
