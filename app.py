import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Nifty Live OI Scalper", layout="wide")

st.title("🎯 Nifty 5M Live OI & Chart Tracker")

# --- Sidebar Inputs ---
st.sidebar.header("⚙️ Market Parameters")
call_wall = st.sidebar.number_input("Major Call Wall (Resistance)", value=22700.0)
pivot_level = st.sidebar.number_input("Pivot / Retest Zone", value=22650.0)
put_wall = st.sidebar.number_input("Major Put Wall (Support)", value=22600.0)

spot_price = st.sidebar.number_input("Current Spot Price", value=22635.0)

# --- Signal Engine ---
st.subheader("📊 Live Structure Status")

col1, col2, col3 = st.columns(3)
col1.metric("Call Resistance", f"{call_wall}")
col2.metric("Pivot Level", f"{pivot_level}")
col3.metric("Put Support", f"{put_wall}")

if spot_price > pivot_level:
    st.success("🟢 BULLISH SQUEEZE ZONE: Price is holding above Pivot. Look for CALL Retest Scalps.")
elif spot_price < pivot_level:
    st.error("🔴 BEARISH BREAKDOWN ZONE: Price is below Pivot. Look for PUT Rejection Scalps.")
else:
    st.warning("⚠️ NEUTRAL / BATTLEGROUND ZONE: Wait for 5M Candle Closing.")

# --- Interactive Visual Chart ---
st.subheader("📉 Level & Zone Visualization")

fig = go.Figure()

# Plot Levels
fig.add_hline(y=call_wall, line_color="red", line_width=2, annotation_text="Call Wall (Resistance)")
fig.add_hline(y=pivot_level, line_color="orange", line_dash="dash", annotation_text="Pivot Zone")
fig.add_hline(y=put_wall, line_color="green", line_width=2, annotation_text="Put Wall (Support)")

# Plot Current Spot Level
fig.add_trace(go.Scatter(
    x=["Current Price"],
    y=[spot_price],
    mode="markers+text",
    name="Spot Price",
    text=[f"Nifty Spot: {spot_price}"],
    textposition="top center",
    marker=dict(color="blue", size=15)
))

fig.update_layout(
    height=400,
    yaxis_range=[put_wall - 100, call_wall + 100],
    template="plotly_dark",
    margin=dict(l=20, r=20, t=30, b=20)
)

st.plotly_chart(fig, use_container_width=True)
