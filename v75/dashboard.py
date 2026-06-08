
import streamlit as st, sqlite3, pandas as pd

st.set_page_config(page_title="V7.5 Full", layout="wide")
st.title("Polymarket V7.5 Signal Dashboard")

con = sqlite3.connect("portfolio.db")
df = pd.read_sql_query("select * from snapshots order by id", con)

tabs = st.tabs(["Market Watch","Top Movers","Signals","Paper Trades"])

with tabs[0]:
    st.subheader("Recent Snapshots")
    st.dataframe(df.tail(30), use_container_width=True)

with tabs[1]:
    rows=[]
    for m in df["market"].unique():
        s=df[df["market"]==m].tail(2)
        if len(s)==2:
            prev=float(s.iloc[0]["yes_price"])
            curr=float(s.iloc[1]["yes_price"])
            ch=((curr-prev)/prev*100) if prev!=0 else 0
            rows.append({
                "market":m,
                "prev_yes":round(prev,4),
                "curr_yes":round(curr,4),
                "change_pct":round(ch,2)
            })
    mv=pd.DataFrame(rows)
    if not mv.empty:
        mv=mv.sort_values("change_pct", ascending=False)
    st.dataframe(mv, use_container_width=True)

with tabs[2]:
    sig=[]
    if 'mv' in locals() and not mv.empty:
        for _,r in mv.iterrows():
            action="WATCH"; reason="Flat"
            if r["change_pct"] > 5:
                action="BUY YES"; reason="Momentum"
            elif r["change_pct"] < -5:
                action="BUY NO"; reason="Reversal"
            sig.append({
                "market":r["market"],
                "signal":action,
                "reason":reason,
                "move_pct":r["change_pct"]
            })
    st.dataframe(pd.DataFrame(sig), use_container_width=True)

with tabs[3]:
    st.write("Paper trade simulator placeholder.")
