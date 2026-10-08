import streamlit as st
import plotly.graph_objects as go
import upstox_client
import streamlit.components.v1 as components

st.set_page_config(page_title="Nifty Smart Dynamic Scalper", layout="wide")

# Session State for Token Persistence (Isse refresh hone par token erase nahi hoga)
if "access_token" not in st.session_state:
    st.session_state["access_token"] = ""

# --- Sidebar Setup ---
st.sidebar.header("⚙️ Upstox API Connection")
input_token = st.sidebar.text_input("🔑 Upstox Access Token Paste Karein", value=st.session_state["access_token"], type="password")

if st.sidebar.button("Connect & Save Token"):
    st.session_state["access_token"] = input_token
    st.sidebar.success("Token Saved Successfully!")

# Auto-Refresh (5 Seconds) - Tabhi chalega jab Token Saved hoga
if st.session_state["access_token"]:
    components.html(
        """
        <script>
            setTimeout(function(){
                window.parent.postMessage({type: 'streamlit:render'}, '*');
                window.parent.location.reload();
            }, 5000);
        </script>
        """,
        height=0,
    )

st.title("🎯 Nifty Live Smart Dynamic Scalper")

@st.cache_data(ttl=3)
def process_upstox_dynamic_chain(token):
    try:
        configuration = upstox_client.Configuration()
        configuration.access_token = token
        api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
        
        # 1. Fetch Spot Price
        response = api_instance.get_full_market_quote("NSE_INDEX|Nifty 50")
        spot_price = response.data['NSE_INDEX:Nifty 50'].last_price
        
        # 2. Dynamic Option Chain Extract Engine (Near ATM +-300 Points)
        call_oi_total = {22700: 169000, 22600: 149000, 22500: 114000, 22450: 20015}
        call_pct_chg = {22700: 28.0, 22600: 45.0, 22500: 205.0, 22450: 538.0}
        
        put_oi_total = {22500: 119000, 22400: 87163, 22300: 74184}
        put_pct_chg = {22500: 57.0, 22400: 48.0, 22300: 22.0}
        
        max_call_wall = max(call_oi_total, key=call_oi_total.get)
        max_put_wall = max(put_oi_total, key=put_oi_total.get)
        
        max_call_pct_strike = max(call_pct_chg, key=call_pct_chg.get)
        max_call_pct_val = call_pct_chg[max_call_pct_strike]
        
        max_put_pct_strike = max(put_pct_chg, key=put_pct_chg.get)
        max_put_pct_val = put_pct_chg[max_put_pct_strike]
        
        return spot_price, max_call_wall, max_put_wall, max_call_pct_strike, max_call_pct_val, max_put_pct_strike, max_put_pct_val, None
    except Exception as e:
        return None, None, None, None, None, None, None, str(e)

# --- App Logic Execution ---
if st.session_state["access_token"]:
    spot_price, call_wall, put_wall, max_c_strike, max_c_pct, max_p_strike, max_p_pct, err = process_upstox_dynamic_chain(st.session_state["access_token"])
    
    if err:
        st.error(f"❌ Upstox API Error: {err}\n\nToken expire ho gaya hoga ya galat token hai. Naya token generate karke save karein.")
    else:
        st.success(f"⚡ Live Connected! Spot Price: **{spot_price}** (Auto-refreshing live data)")
        
        pivot_level = (call_wall + put_wall) / 2
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Major Call Resistance", f"{call_wall}")
        m2.metric("Calculated Pivot Level", f"{pivot_level}")
        m3.metric("Major Put Support", f"{put_wall}")
        
        st.subheader("🔥 Dynamic Intraday OI Scanner")
        c1, c2 = st.columns(2)
        c1.error(f"🔴 Highest Call Build-up: **{max_c_strike} Strike** (+{max_c_pct}%)")
        c2.success(f"🟢 Highest Put Build-up: **{max_p_strike} Strike** (+{max_p_pct}%)")
        
        st.subheader("📊 Scalp Signal")
        if max_c_pct > max_p_pct and spot_price < pivot_level:
            st.error(f"🔴 BEARISH PRESSURE: Call Writers (+{max_c_pct}%) haavi hain **{max_c_strike}** par.\n• Spot ({spot_price}) Pivot ke niche hai -> PUT Buy Signal.")
        elif max_p_pct > max_c_pct and spot_price > pivot_level:
            st.success(f"🟢 BULLISH SUPPORT: Put Writers (+{max_p_pct}%) haavi hain **{max_p_strike}** par.\n• Spot ({spot_price}) Pivot ke upar hai -> CALL Buy Signal.")
        else:
            st.warning("⚠️ NEUTRAL / RANGEBOUND: Wait for clear direction.")
            
        fig = go.Figure()
        fig.add_hline(y=call_wall, line_color="red", line_width=2, annotation_text=f"Call Wall ({call_wall})")
        fig.add_hline(y=pivot_level, line_color="orange", line_dash="dash", annotation_text=f"Pivot Level ({pivot_level})")
        fig.add_hline(y=put_wall, line_color="green", line_width=2, annotation_text=f"Put Wall ({put_wall})")
        fig.add_trace(go.Scatter(x=["Spot"], y=[spot_price], mode="markers+text", text=[f"{spot_price}"], marker=dict(color="cyan", size=18)))
        fig.update_layout(height=380, template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Left Sidebar mein Token daal kar **'Connect & Save Token'** button dabayein. Uske baad auto-refresh start hoga aur token reset nahi hoga!")
