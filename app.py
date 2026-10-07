import streamlit as st
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components

st.set_page_config(page_title="Nifty OI Scalper", layout="wide")

# --- Auto Refresh Script (10 Seconds for IP Safety) ---
components.html(
    """
    <script>
        setTimeout(function(){
            window.parent.postMessage({type: 'streamlit:render'}, '*');
            window.parent.location.reload();
        }, 10000); // 10 Seconds Reload
    </script>
    """,
    height=0,
)

st.title("🎯 Nifty Live OI Scalper")

@st.cache_data(ttl=8)
def get_live_nse_data():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=3)
        response = session.get(url, headers=headers, timeout=3)
        
        if response.status_code != 200:
            return None, None, None, None, "Blocked"
            
        data = response.json()
        spot_price = data['records']['underlyingValue']
        records = data['records']['data']
        
        call_oi_map = {}
        put_oi_map = {}
        
        for record in records:
            strike = record['strikePrice']
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

spot_price, call_wall, pivot_level, put_wall, error = get_live_nse_data()

# Status Banner & Controls
if error or spot_price is None:
    st.info("💡 NSE Live Auto-Fetch Busy (IP Restriction). Using Manual Inputs below:")
    col_a, col_b = st.columns(2)
    with col_a:
        spot_price = st.number_input("Nifty Spot Price", value=22635.0, step=0.5)
        call_wall = st.number_input("Call Resistance (Call Wall)", value=22700.0, step=50.0)
    with col_b:
        pivot_level = st.number_input("Pivot Zone", value=22650.0, step=50.0)
        put_wall = st.number_input("Put Support (Put Wall)", value=22600.0, step=50.0)
else:
    st.success(f"⚡ Live NSE Connected! Nifty Spot: **{spot_price}**")

# Metrics Display
col1, col2, col3 = st.columns(3)
col1.metric("Call Wall (Resistance)", f"{call_wall}")
col2.metric("Pivot Zone", f"{pivot_level}")
col3.metric("Put Wall (Support)", f"{put_wall}")

# Signal Logic
st.subheader("📊 Live Signal Alert")
if spot_price > pivot_level:
    st.success("🟢 BULLISH ZONE: Price holding above Pivot. Look for CALL Buy.")
elif spot_price < pivot_level:
    st.error("🔴 BEARISH ZONE: Price below Pivot. Look for PUT Buy.")
else:
    st.warning("⚠️ NEUTRAL ZONE: Rangebound market.")

# Visual Chart
fig = go.Figure()
fig.add_hline(y=call_wall, line_color="red", line_width=2, annotation_text=f"Call Wall ({call_wall})")
fig.add_hline(y=pivot_level, line_color="orange", line_dash="dash", annotation_text=f"Pivot Zone ({pivot_level})")
fig.add_hline(y=put_wall, line_color="green", line_width=2, annotation_text=f"Put Wall ({put_wall})")

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
