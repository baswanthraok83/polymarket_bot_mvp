
import streamlit as st, sqlite3, pandas as pd
st.set_page_config(page_title="V6.5 Analytics", layout="wide")
st.title("Polymarket V6.5 Analytics Pack")
con=sqlite3.connect("portfolio.db")
df=pd.read_sql_query("select * from trades", con)
tab1,tab2,tab3=st.tabs(["Executive Summary","Trader Deep Dive","AI Insights"])
with tab1:
    st.metric("Total PnL", round(df["pnl"].sum(),2))
    st.metric("Win Rate %", round((df["pnl"]>0).mean()*100,1))
    st.line_chart(df["pnl"].cumsum())
with tab2:
    st.subheader("By Category")
    st.bar_chart(df.groupby("category")["pnl"].sum())
    st.dataframe(df, use_container_width=True)
with tab3:
    best=df.groupby("category")["pnl"].sum().idxmax()
    worst=df.groupby("category")["pnl"].sum().idxmin()
    st.write(f"Best category: {best}")
    st.write(f"Weakest category: {worst}")
    st.write("Suggestion: Increase focus on best category, reduce weak category exposure.")
