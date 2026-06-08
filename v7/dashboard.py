import streamlit as st
from modules.feed import fetch_real_markets
st.set_page_config(page_title='V7 Real Data', layout='wide')
st.title('Polymarket V7 Real Data')
df=fetch_real_markets()
st.dataframe(df, use_container_width=True)
