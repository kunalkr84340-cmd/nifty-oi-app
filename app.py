import streamlit as st
import plotly.graph_objects as go
import requests
import streamlit.components.v1 as components

st.set_page_config(page_title="Nifty Smart Live Scalper", layout="wide")

query_params = st.query_params
current_token = query_params.get("token", "")

st.sidebar.header("⚙️ Upstox API Connection")
input_token = st.sidebar.text_input("🔑 Upstox Access Token Paste Karein", value=current_token, type="password")

if st.sidebar.button("Connect & Permanent Save"):
    if input_token:
        st.query_params["token"] = input_token
        st.sidebar.success("✅ Token Saved!")
        st.rerun()

active_token = query_params.get("token", "")

if active_token:
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

st.title("🎯 Nifty Live Smart Dynamic Scalper")

@st.cache_data(ttl=2)
def fetch_upstox_data(token):
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    try:
        # 1. Fetch Spot Price
        spot_url = "https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX|Nifty 50"
        spot_res = requests.get(spot_url, headers=headers).json()
        
        if spot_res.get('status') != 'success':
            return None, None, None, None, None, None, None, "Invalid Access Token or Token Expired."
            
        spot_data = spot_res['data']['NSE_INDEX:Nifty 50']
        spot_price = spot_data['last_price']
        
        # 2. Fetch Nearest Expiry Date
        contracts_url = "https://api.upstox.com/v2/option/contract?instrument_key=NSE_INDEX|Nifty 50"
        contracts_res = requests.get(contracts_url, headers=headers).json()
        
        expiries = sorted(list(set([x.get('expiry') for x in contracts_res.get('data', []) if x.get('expiry')])))
        if not expiries:
            return None, None, None, None, None, None, None, "Option contracts load nahi ho paye."
            
        nearest_expiry = expiries[0]
        
        # 3. Fetch Option Chain Data
        chain_url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={nearest_expiry}"
        chain_res = requests.get(chain_url, headers=headers).json()
        
        call_oi_total = {}
        call_pct_chg = {}
        put_oi_total = {}
        put_pct_chg = {}
        
        for item in chain_res.get('data', []):
            strike = item.get('strike_price', 0)
            if abs(strike - spot_price) <= 350:
                # Call Data Extraction
                call_opts = item.get('call_options', {})
                if call_opts:
                    c_mkt = call_opts.get('market_data', {})
                    c_oi = c_mkt.get('oi', 0)
                    call_oi_total[strike] = c_oi
                    
                    # Direct p_change fallback to manual formula if zero/null
                    c_pct = c_mkt.get('p_change', 0.0)
                    if not c_pct or c_pct == 0:
                        prev_oi = c_mkt.get('prev_oi', 1)
                        if prev_oi > 0:
                            c_pct = ((c_oi - prev_oi) / prev_oi) * 100
                    call_pct_chg[strike] = round(float(c_pct), 1)
                    
                # Put Data Extraction
                put_opts = item.get('put_options', {})
                if put_opts:
                    p_mkt = put_opts.get('market_data', {})
                    p_oi = p_mkt.get('oi', 0)
                    put_oi_total[strike] = p_oi
                    
                    p_pct = p_mkt.get('p_change', 0.0)
                    if not p_pct or p_pct == 0:
                        prev_oi = p_mkt.get('prev_oi', 1)
                        if prev_oi > 0:
                            p_pct = ((p_oi - prev_oi) / prev_oi) * 100
                    put_pct_chg[strike] = round(float(p_pct), 1)

        if not call_pct_chg or not put_pct_chg:
            return None, None, None, None, None, None, None, "OI Data Null/Empty aa raha hai."

        max_call_wall = max(call_oi_total, key=call_oi_total.get)
        max_put_wall = max(put_oi_total, key=put_oi_total.get)
        
        max_call_pct_strike = max(call_pct_chg, key=call_pct_chg.get)
        max_call_pct_val = call_pct_chg[max_call_pct_strike]
        
        max_put_pct_strike = max(put_pct_chg, key=put_pct_chg.get)
        max_put_pct_val = put_pct_chg[max_put_pct_strike]
        
        return spot_price, max_call_wall, max_put_wall, max_call_pct_strike, max_call_pct_val, max_put_pct_strike, max_put_pct_val, None

    except Exception as e:
        return None, None, None, None, None, None, None, str(e)

# --- App Render ---
if active_token:
    spot_price, call_wall, put_wall, max_c_strike, max_c_pct, max_p_strike, max_p_pct, err = fetch_upstox_data(active_token)
    
    if err:
        st.error(f"⚠️ Status: {err}")
        st.info("💡 Upstox Developer Console se naya Access Token generate karke yahan paste karein.")
        if st.button("Reset Token"):
            st.query_params.clear()
            st.rerun()
    else:
        st.success(f"⚡ Live Connected! Nifty Spot: **{spot_price}** (Auto Refreshing 5s)")
        
        pivot_level = (call_wall + put_wall) / 2
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Major Call Resistance", f"{call_wall}")
        m2.metric("Calculated Pivot Level", f"{pivot_level}")
        m3.metric("Major Put Support", f"{put_wall}")
        
        st.subheader("🔥 Dynamic Intraday OI Scanner")
        c1, c2 = st.columns(2)
        c1.error(f"🔴 Highest Call Build-up: **{max_c_strike} Strike** (+{max_c_pct}%)")
        c2.success(f"🟢 Highest Put Build-up: **{max_p_strike} Strike** (+{max_p_pct}%)")
        
        st.subheader("📊 Live Scalp Signal")
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
    st.info("👈 Left Sidebar mein apna **Upstox Access Token** paste karke **'Connect & Permanent Save'** dabaayein.")
        
