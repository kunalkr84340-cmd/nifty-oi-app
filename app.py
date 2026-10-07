import stre
import plotly.graph_objects as go
import requests
import pandas as pd

st.set_page_config(page_title="Nifty Live Auto OI Scalper", layout="wide")

st.title("🎯 Nifty Live Auto-OI Scalper")

# Function to fetch live NSE Option Chain & Spot Price
@st.cache_data(ttl=15)
def get_live_nse_data():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    session = requests.Session()
    try:
        # First hit homepage to get cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)
        data = response.json()
        
        spot_price = data['records']['underlyingValue']
        records = data['records']['data']
        
        call_oi_map = {}
        put_oi_map = {}
        
        for record in records:
            strike = record['strikePrice']
            # Filter nearby strikes around spot
            if spot_price - 1000 <= strike <= spot_price + 1000:
                if 'CE' in record:
                    call_oi_map[strike] = record['CE']['openInterest']
                if 'PE' in record:
                    put_oi_map[strike] = record['PE']['openInterest']
                    
        max_call_wall = max(call_oi_map, key=call_oi_map.get) if call_oi_map else spot_price + 100
        max_put_wall = max(put_oi_map, key=put_oi_map.get) if put_oi_map else spot_price - 100
        pivot_zone = (max_call_wall + max_put_wall) / 2
        
        return spot_price, max_call_wall, pivot_zone, max_put_wall, None
    except Exception as e:
        return None, None, None, None, str(e)

# Auto Refresh Button
if st.button("🔄 Refresh Live Data"):
    st.cache_data.clear()

spot_price, call_wall, pivot_level, put_wall, error = get_live_nse_data()

if error or spot_price is None:
    st.warning("⚠️ NSE Server connection busy. Showing fallback manual inputs.")
    spot_price = st.sidebar.number_input("Current Spot Price", value=22635.0)
    call_wall = st.sidebar.number_input("Call Wall", value=22700.0)
    pivot_level = st.sidebar.number_input("Pivot Zone", value=22650.0)
    put_wall = st.sidebar.number_input("Put Wall", value=22600.0)
else:
    st.success(f"✅ Live NSE Data Connected! Nifty Spot: **{spot_price}**")

# Metrics Display
col1, col2, col3 = st.columns(3)
col1.metric("Max Call Wall (Resistance)", f"{call_wall}")
col2.metric("Calculated Pivot Zone", f"{pivot_level}")
col3.metric("Max Put Wall (Support)", f"{put_wall}")

# Signal Logic
st.subheader("📊 Live Auto Signal")
if spot_price > pivot_level:
    st.success("🟢 BULLISH ZONE: Price holding above Pivot. Look for CALL Buy on Dip.")
elif spot_price < pivot_level:
    st.error("🔴 BEARISH ZONE: Price below Pivot. Look for PUT Buy on Rise.")
else:
    st.warning("⚠️ NEUTRAL ZONE: Rangebound market.")

# Visual Chart
fig = go.Figure()
fig.add_hline(y=call_wall, line_color="red", line_width=2, annotation_text=f"Call Resistance ({call_wall})")
fig.add_hline(y=pivot_level, line_color="orange", line_dash="dash", annotation_text=f"Pivot Zone ({pivot_level})")
fig.add_hline(y=put_wall, line_color="green", line_width=2, annotation_text=f"Put Support ({put_wall})")

fig.add_trace(go.Scatter(
    x=["Live Price"],
    y=[spot_price],
    mode="markers+text",
    name="Nifty Spot",
    text=[f"Spot: {spot_price}"],
    textposition="top center",
    marker=dict(color="cyan", size=16)
))

fig.update_layout(height=400, template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig, use_container_width=True)
