import streamlit as st
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components

st.set_page_config(page_title="Nifty Live % OI Scalper", layout="wide")

# --- Mode Selection (Sidebar) ---
st.sidebar.header("⚙️ Data Settings")
data_mode = st.sidebar.radio("Data Mode Select Karein:", ["Auto Fetch (Live NSE)", "Manual Input Mode"])

# --- Auto Refresh Script (Only active in Auto Mode) ---
if data_mode == "Auto Fetch (Live NSE)":
    components.html(
        """
        <script>
            setTimeout(function(){
                window.parent.postMessage({type: 'streamlit:render'}, '*');
                window.parent.location.reload();
            }, 10000);
        </script>
        """,
        height=0,
    )

st.title("🎯 Nifty Live Scalper Dashboard")

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
            return None, None, None, None, None, None, "Blocked"
            
        data = response.json()
        spot_price = data['records']['underlyingValue']
        records = data['records']['data']
        
        call_oi_map, put_oi_map = {}, {}
        call_pct_map, put_pct_map = {}, {}
        
        for record in records:
            strike = record['strikePrice']
            if spot_price - 1000 <= strike <= spot_price + 1000:
                if 'CE' in record:
                    ce_oi = record['CE']['openInterest']
                    ce_chg = record['CE']['changeinOpenInterest']
                    call_oi_map[strike] = ce_oi
                    prev_ce_oi = ce_oi - ce_chg
                    call_pct_map[strike] = round((ce_chg / prev_ce_oi * 100), 1) if prev_ce_oi > 0 else 0

                if 'PE' in record:
                    pe_oi = record['PE']['openInterest']
                    pe_chg = record['PE']['changeinOpenInterest']
                    put_oi_map[strike] = pe_oi
                    prev_pe_oi = pe_oi - pe_chg
                    put_pct_map[strike] = round((pe_chg / prev_pe_oi * 100), 1) if prev_pe_oi > 0 else 0
                    
        max_call_wall = max(call_oi_map, key=call_oi_map.get) if call_oi_map else spot_price + 100
        max_put_wall = max(put_oi_map, key=put_oi_map.get) if put_oi_map else spot_price - 100
        pivot_zone = (max_call_wall + max_put_wall) / 2
        
        call_pct_chg = call_pct_map.get(max_call_wall, 0.0)
        put_pct_chg = put_pct_map.get(max_put_wall, 0.0)
        
        return spot_price, max_call_wall, pivot_zone, max_put_wall, call_pct_chg, put_pct_chg, None
    except Exception as e:
        return None, None, None, None, None, None, str(e)

# Mode Decision Logic
if data_mode == "Auto Fetch (Live NSE)":
    spot_price, call_wall, pivot_level, put_wall, call_pct, put_pct, error = get_live_nse_data()
    if error or spot_price is None:
        st.error("⚠️ NSE Live Busy! Left Sidebar se 'Manual Input Mode' select karein taaki auto-refresh stop ho jaye.")
    else:
        st.success(f"⚡ Live NSE Connected! Nifty Spot: **{spot_price}** (Refreshing every 10s)")
else:
    st.info("📌 Manual Mode Active: Auto-refresh disabled hai. Aap aaram se numbers Type kar sakte hain.")
    spot_price, call_wall, pivot_level, put_wall, call_pct, put_pct = None, None, None, None, None, None

# Manual Inputs Panel (Always stable when Manual Mode is selected)
if data_mode == "Manual Input Mode" or spot_price is None:
    col_a, col_b = st.columns(2)
    with col_a:
        spot_price = st.number_input("Nifty Spot Price", value=22635.0, step=0.5)
        call_wall = st.number_input("Call Resistance (Call Wall)", value=22700.0, step=50.0)
        call_pct = st.number_input("Call OI % Change", value=-12.5)
    with col_b:
        pivot_level = st.number_input("Pivot Zone", value=22650.0, step=50.0)
        put_wall = st.number_input("Put Support (Put Wall)", value=22600.0, step=50.0)
        put_pct = st.number_input("Put OI % Change", value=28.4)

# Candle Pattern Selector
st.subheader("🕯️ Live 5-Min Candle Pattern")
candle_pattern = st.selectbox(
    "Chart par konsa Pattern hai?",
    ["None / Normal Candle", "Bullish Pin Bar (Hammer) 🔨", "Bearish Pin Bar (Shooting Star) ☄️", "Bullish Engulfing 🟢", "Bearish Engulfing 🔴"]
)

# Metrics Display
col1, col2, col3 = st.columns(3)
col1.metric("Call Resistance", f"{call_wall}", delta=f"OI: {call_pct}%")
col2.metric("Pivot Zone", f"{pivot_level}")
col3.metric("Put Support", f"{put_wall}", delta=f"OI: {put_pct}%")

# Signal Logic
st.subheader("📊 OI % Change Alert & Action")

if call_pct <= -15.0:
    st.success(f"🔥 SHORT COVERING WARNING! Call Writers {call_pct}% exit kar chuke hain.")
elif call_pct >= 30.0:
    st.warning(f"🛡️ STRONG CALL RESISTANCE: Call OI +{call_pct}% badha hai.")

if put_pct <= -15.0:
    st.error(f"📉 SUPPORT UNWINDING WARNING! Put Writers {put_pct}% exit kar chuke hain.")
elif put_pct >= 30.0:
    st.success(f"🛡️ STRONG PUT SUPPORT: Put OI +{put_pct}% badha hai.")

if spot_price > pivot_level:
    if "Bullish" in candle_pattern:
        st.success(f"🔥 HIGH CONVICTION CALL BUY!\n\n• Target: {call_wall} | SL: {spot_price - 15}")
    else:
        st.info(f"🟢 BULLISH ZONE: Price Pivot ke upar hai. Dip par CALL Buy dekho.")
elif spot_price < pivot_level:
    if "Bearish" in candle_pattern:
        st.error(f"🔥 HIGH CONVICTION PUT BUY!\n\n• Target: {put_wall} | SL: {spot_price + 15}")
    else:
        st.warning(f"🔴 BEARISH ZONE: Price Pivot ke niche hai. Bounce par PUT Buy dekho.")

# Visual Plotly Chart
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

fig.update_layout(height=380, template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig, use_container_width=True)
