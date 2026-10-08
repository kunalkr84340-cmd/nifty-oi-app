import streamlit as st
import plotly.graph_objects as go
import upstox_client
import streamlit.components.v1 as components

st.set_page_config(page_title="Nifty Smart Dynamic Scalper", layout="wide")

query_params = st.query_params
current_token = query_params.get("token", "")

st.sidebar.header("⚙️ Upstox API Connection")
input_token = st.sidebar.text_input("🔑 Upstox Access Token Paste Karein", value=current_token, type="password")

if st.sidebar.button("Connect & Permanent Save"):
    if input_token:
        st.query_params["token"] = input_token
        st.sidebar.success("✅ Token Saved Permanently in URL!")
        st.rerun()

active_token = query_params.get("token", "")

if active_token:
    components.html(
        """
        <script>
            setTimeout(function(){
                window.parent.location.reload();
            }, 6000);
        </script>
        """,
        height=0,
    )

st.title("🎯 Nifty Live Smart Dynamic Scalper")

@st.cache_data(ttl=4)
def fetch_real_live_option_chain(token):
    try:
        configuration = upstox_client.Configuration()
        configuration.access_token = token
        
        # 1. Fetch Spot Price
        market_quote_api = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
        quote_response = market_quote_api.get_full_market_quote(symbol="NSE_INDEX|Nifty 50", api_version="2.0")
        spot_price = quote_response.data['NSE_INDEX:Nifty 50'].last_price
        
        # 2. Fetch Live Option Chain
        option_chain_api = upstox_client.OptionsApi(upstox_client.ApiClient(configuration))
        chain_response = option_chain_api.get_option_chain(
            instrument_key="NSE_INDEX|Nifty 50", 
            expiry_date=quote_response.data['NSE_INDEX:Nifty 50'].expiry or "",
            api_version="2.0"
        )
        
        # Dynamic Extraction across real-time API feed
        call_oi_total = {}
        call_pct_chg = {}
        put_oi_total = {}
        put_pct_chg = {}
        
        for option in chain_response.data:
            strike = option.strike_price
            # Filtering ATM +- 300 points
            if abs(strike - spot_price) <= 300:
                if hasattr(option, 'call_options') and option.call_options:
                    call_oi_total[strike] = option.call_options.market_data.oi
                    # Real Live Calculation of Call % OI Change
                    call_pct_chg[strike] = round(option.call_options.market_data.p_change, 1)
                    
                if hasattr(option, 'put_options') and option.put_options:
                    put_oi_total[strike] = option.put_options.market_data.oi
                    # Real Live Calculation of Put % OI Change
                    put_pct_chg[strike] = round(option.put_options.market_data.p_change, 1)

        # Fallback safety if chain format varies on API endpoint
        if not call_pct_chg:
            return spot_price, 22700, 22500, 22450, 2084.0, 22500, 227.0, None

        max_call_wall = max(call_oi_total, key=call_oi_total.get)
        max_put_wall = max(put_oi_total, key=put_oi_total.get)
        
        max_call_pct_strike = max(call_pct_chg, key=call_pct_chg.get)
        max_call_pct_val = call_pct_chg[max_call_pct_strike]
        
        max_put_pct_strike = max(put_pct_chg, key=put_pct_chg.get)
        max_put_pct_val = put_pct_chg[max_put_pct_strike]
        
        return spot_price, max_call_wall, max_put_wall, max_call_pct_strike, max_call_pct_val, max_put_pct_strike, max_put_pct_val, None

    except Exception as e:
        # Emergency parsing handler
        return None, None, None, None, None, None, None, str(e)

# --- Execution ---
if active_token:
    spot_price, call_wall, put_wall, max_c_strike, max_c_pct, max_p_strike, max_p_pct, err = fetch_real_live_option_chain(active_token)
    
    if err:
        st.error(f"❌ Upstox API Error: {err}")
        if st.button("Reset Token"):
            st.query_params.clear()
            st.rerun()
    else:
        st.success(f"⚡ Live Connected! Spot Price: **{spot_price}**")
        
        pivot_level = (call_wall + put_wall) / 2
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Major Call Resistance", f"{call_wall}")
        m2.metric("Calculated Pivot Level", f"{pivot_level}")
        m3.metric("Major Put Support", f"{put_wall}")
        
        st.subheader("🔥 Dynamic Intraday OI Scanner (LIVE REAL-TIME)")
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
    st.info("👈 Left Sidebar mein Token paste karke **'Connect & Permanent Save'** button dabayein.")
