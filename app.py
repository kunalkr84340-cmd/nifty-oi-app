import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="Nifty Live OI Scalper Engine", layout="wide")

st.title("🎯 Nifty Live Smart OI Scalper Engine")

# Auto Reload Script Every 5 Seconds
components.html(
    """
    <script>
        setTimeout(function(){
            window.parent.location.reload();
        }, 5000);
    </script>
    """,
    height=0,
)

@st.cache_data(ttl=3)
def fetch_nse_live_option_chain():
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9'
    }
    
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    session = requests.Session()
    
    try:
        # Initial request to obtain cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return None, None, None, None, None, None, None, f"NSE Server Status Code: {response.status_code}"
            
        json_data = response.json()
        records = json_data.get('records', {})
        spot_price = records.get('underlyingValue', 0.0)
        data = records.get('data', [])
        
        call_oi_dict = {}
        call_pct_dict = {}
        put_oi_dict = {}
        put_pct_dict = {}
        
        for row in data:
            strike = row.get('strikePrice', 0)
            
            # Filter Strikes near Spot Price (Spot +- 350 points)
            if abs(strike - spot_price) <= 350:
                if 'CE' in row:
                    ce = row['CE']
                    call_oi_dict[strike] = ce.get('openInterest', 0)
                    call_pct_dict[strike] = round(ce.get('pchangeinOpenInterest', 0.0), 1)
                    
                if 'PE' in row:
                    pe = row['PE']
                    put_oi_dict[strike] = pe.get('openInterest', 0)
                    put_pct_dict[strike] = round(pe.get('pchangeinOpenInterest', 0.0), 1)

        if not call_pct_dict or not put_pct_dict:
            return None, None, None, None, None, None, None, "Option Chain Data stream loading..."

        max_call_wall = max(call_oi_dict, key=call_oi_dict.get)
        max_put_wall = max(put_oi_dict, key=put_oi_dict.get)
        
        max_call_pct_strike = max(call_pct_dict, key=call_pct_dict.get)
        max_call_pct_val = call_pct_dict[max_call_pct_strike]
        
        max_put_pct_strike = max(put_pct_dict, key=put_pct_dict.get)
        max_put_pct_val = put_pct_dict[max_put_pct_strike]
        
        return spot_price, max_call_wall, max_put_wall, max_call_pct_strike, max_call_pct_val, max_put_pct_strike, max_put_pct_val, None

    except Exception as e:
        return None, None, None, None, None, None, None, str(e)

# --- Execution ---
spot_price, call_wall, put_wall, max_c_strike, max_c_pct, max_p_strike, max_p_pct, err = fetch_nse_live_option_chain()

if err:
    st.warning(f"⏳ Live Feed Fetching Status: {err}")
    st.info("💡 Tip: NSE Server response delay ho raha hai, 5 second me auto retry ho jayega.")
else:
    st.success(f"⚡ Live Connected! Nifty Spot Price: **{spot_price}** (Auto Refreshing 5s)")
    
    pivot_level = (call_wall + put_wall) / 2
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Major Call Resistance", f"{call_wall}")
    m2.metric("Calculated Pivot Level", f"{pivot_level}")
    m3.metric("Major Put Support", f"{put_wall}")
    
    st.subheader("🔥 Dynamic Intraday OI Scanner (NSE LIVE)")
    c1, c2 = st.columns(2)
    c1.error(f"🔴 Highest Call Build-up: **{max_c_strike} Strike** (+{max_c_pct}%)")
    c2.success(f"🟢 Highest Put Build-up: **{max_p_strike} Strike** (+{max_p_pct}%)")
    
    st.subheader("📊 Live Scalp Signal Analysis")
    if max_c_pct > max_p_pct and spot_price < pivot_level:
        st.error(f"🔴 BEARISH PRESSURE: Call Writers (+{max_c_pct}%) haavi hain **{max_c_strike}** par.\n• Spot ({spot_price}) Pivot ke niche hai -> PUT Buy Signal Active.")
    elif max_p_pct > max_c_pct and spot_price > pivot_level:
        st.success(f"🟢 BULLISH SUPPORT: Put Writers (+{max_p_pct}%) haavi hain **{max_p_strike}** par.\n• Spot ({spot_price}) Pivot ke upar hai -> CALL Buy Signal Active.")
    else:
        st.warning("⚠️ NEUTRAL / RANGEBOUND: Waiting for clear direction & break.")
        
    fig = go.Figure()
    fig.add_hline(y=call_wall, line_color="red", line_width=2, annotation_text=f"Call Wall ({call_wall})")
    fig.add_hline(y=pivot_level, line_color="orange", line_dash="dash", annotation_text=f"Pivot Level ({pivot_level})")
    fig.add_hline(y=put_wall, line_color="green", line_width=2, annotation_text=f"Put Wall ({put_wall})")
    fig.add_trace(go.Scatter(x=["Spot"], y=[spot_price], mode="markers+text", text=[f"{spot_price}"], marker=dict(color="cyan", size=18)))
    fig.update_layout(height=380, template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)
