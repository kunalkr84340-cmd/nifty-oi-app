import streamlit as st
import plotly.graph_objects as go
import requests
import time

st.set_page_config(page_title="Nifty Smart OI Analyst Engine", layout="wide")

query_params = st.query_params
current_token = query_params.get("token", "")

st.sidebar.header("⚙️ Upstox API Connection")
input_token = st.sidebar.text_input("🔑 Upstox Access Token Paste Karein", value=current_token, type="password")

if st.sidebar.button("Connect & Permanent Save"):
    if input_token:
        st.query_params["token"] = input_token
        st.sidebar.success("✅ Token Saved Permanently!")
        st.rerun()

active_token = query_params.get("token", "")

st.title("🎯 Nifty Live Smart Dynamic Analyst Engine")

@st.cache_data(ttl=5)
def fetch_and_analyze_upstox_data(token):
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    try:
        # 1. Fetch Spot Price
        spot_url = "https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX|Nifty 50"
        spot_res = requests.get(spot_url, headers=headers).json()
        
        if spot_res.get('status') != 'success':
            return None, "Invalid Access Token or Expired Token."
            
        spot_price = spot_res['data']['NSE_INDEX:Nifty 50']['last_price']
        
        # 2. Fetch Nearest Expiry Date
        contracts_url = "https://api.upstox.com/v2/option/contract?instrument_key=NSE_INDEX|Nifty 50"
        contracts_res = requests.get(contracts_url, headers=headers).json()
        
        expiries = sorted(list(set([x.get('expiry') for x in contracts_res.get('data', []) if x.get('expiry')])))
        if not expiries:
            return None, "Expiry contracts load nahi ho paye."
            
        nearest_expiry = expiries[0]
        
        # 3. Fetch Full Option Chain Data
        chain_url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={nearest_expiry}"
        chain_res = requests.get(chain_url, headers=headers).json()
        
        call_oi_map = {}
        call_pct_map = {}
        put_oi_map = {}
        put_pct_map = {}
        
        for item in chain_res.get('data', []):
            strike = item.get('strike_price', 0)
            if abs(strike - spot_price) <= 400:
                # Call Extraction
                c_opts = item.get('call_options', {})
                if c_opts:
                    c_mkt = c_opts.get('market_data', {})
                    c_oi = c_mkt.get('oi', 0)
                    call_oi_map[strike] = c_oi
                    
                    c_pct = c_mkt.get('p_change', 0.0)
                    if not c_pct or c_pct == 0:
                        prev_oi = c_mkt.get('prev_oi', 1)
                        if prev_oi > 0:
                            c_pct = ((c_oi - prev_oi) / prev_oi) * 100
                    call_pct_map[strike] = round(float(c_pct), 1)
                    
                # Put Extraction
                p_opts = item.get('put_options', {})
                if p_opts:
                    p_mkt = p_opts.get('market_data', {})
                    p_oi = p_mkt.get('oi', 0)
                    put_oi_map[strike] = p_oi
                    
                    p_pct = p_mkt.get('p_change', 0.0)
                    if not p_pct or p_pct == 0:
                        prev_oi = p_mkt.get('prev_oi', 1)
                        if prev_oi > 0:
                            p_pct = ((p_oi - prev_oi) / prev_oi) * 100
                    put_pct_map[strike] = round(float(p_pct), 1)

        if not call_pct_map or not put_pct_map:
            return None, "Option Chain Data Fetch nahi hua."

        # Top 3 High Call OI Build-ups
        top_call_pct = sorted(call_pct_map.items(), key=lambda x: x[1], reverse=True)[:3]
        # Top 3 High Put OI Build-ups
        top_put_pct = sorted(put_pct_map.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Max OI Walls
        max_call_wall = max(call_oi_map, key=call_oi_map.get)
        max_put_wall = max(put_oi_map, key=put_oi_map.get)

        return {
            "spot_price": spot_price,
            "max_call_wall": max_call_wall,
            "max_put_wall": max_put_wall,
            "top_call_pct": top_call_pct,
            "top_put_pct": top_put_pct,
            "call_pct_map": call_pct_map,
            "put_pct_map": put_pct_map
        }, None

    except Exception as e:
        return None, str(e)

# --- App Render ---
if active_token:
    data, err = fetch_and_analyze_upstox_data(active_token)
    
    if err:
        st.error(f"⚠️ Status: {err}")
        st.info("💡 Token Expire hone par naya Token Paste karein.")
        if st.button("Reset Saved Token"):
            st.query_params.clear()
            st.rerun()
    else:
        spot = data['spot_price']
        call_wall = data['max_call_wall']
        put_wall = data['max_put_wall']
        top_calls = data['top_call_pct']
        top_puts = data['top_put_pct']
        
        pivot_level = (call_wall + put_wall) / 2
        
        st.success(f"⚡ Live Connected! Nifty Spot Price: **{spot}**")
        
        # Metrics Row
        m1, m2, m3 = st.columns(3)
        m1.metric("Major Call Resistance", f"{call_wall}")
        m2.metric("Calculated Pivot Level", f"{pivot_level}")
        m3.metric("Major Put Support", f"{put_wall}")
        
        st.markdown("---")
        st.subheader("📊 Dynamic Market Observation & Deep Analysis")
        
        call_build_str = ", ".join([f"**{k} CE (+{v}%)**" for k, v in top_calls])
        put_build_str = ", ".join([f"**{k} PE (+{v}%)**" for k, v in top_puts])
        
        total_top_call_pct = sum([v for k, v in top_calls])
        total_top_put_pct = sum([v for k, v in top_puts])
        
        # 1. Market Pressure Shift Analysis
        if total_top_call_pct > total_top_put_pct * 1.5:
            st.error(
                f"🔴 **Call Writing Heavy Dynamic Shift Detected:**\n"
                f"• Call side par aggressive build-up ho gaya hai: {call_build_str}.\n"
                f"• Above levels completely block ho rahe hain aur market par **Bearish Pressure** haavi hai."
            )
        elif total_top_put_pct > total_top_call_pct * 1.5:
            st.success(
                f"🟢 **Put Writing Strong Dynamic Shift Detected:**\n"
                f"• Put side par aggressive build-up ho raha hai: {put_build_str}.\n"
                f"• Lower levels par strong support mil raha hai aur market par **Bullish Momentum** haavi hai."
            )
        else:
            st.warning("⚠️ **Rangebound / Neutral Pressure:** Call aur Put dono side barabar spikings hain. Wait for break.")

        # 2. Scalp Trade Action Plan
        st.subheader("🎯 Action Plan & Pullback Logic")
        
        if spot < pivot_level and total_top_call_pct > total_top_put_pct:
            best_pullback_strike = top_calls[0][0]
            st.error(
                f"💡 **Trade Advice (PE Side):**\n"
                f"• Spot ({spot}) Pivot level ({pivot_level}) ke niche trade kar raha hai.\n"
                f"• Direct market par PE leke mat phasna. Agar price bounce karke **{best_pullback_strike - 20} - {best_pullback_strike}** zone tak pullback leta hai, toh wahan se **Safe PE Scalp Entry** banegi with small SL."
            )
        elif spot > pivot_level and total_top_put_pct > total_top_call_pct:
            best_pullback_strike = top_puts[0][0]
            st.success(
                f"💡 **Trade Advice (CE Side):**\n"
                f"• Spot ({spot}) Pivot level ({pivot_level}) ke upar hai.\n"
                f"• Dip par buy karo: Agar price **{best_pullback_strike} - {best_pullback_strike + 20}** zone tak aati hai, toh wahan se **Safe CE Scalp Entry** banegi."
            )
        else:
            st.info("💡 **Trade Advice:** Market choppy hai, major support/resistance break hone ka wait karein.")

        # Chart
        fig = go.Figure()
        fig.add_hline(y=call_wall, line_color="red", line_width=2, annotation_text=f"Call Wall ({call_wall})")
        fig.add_hline(y=pivot_level, line_color="orange", line_dash="dash", annotation_text=f"Pivot Level ({pivot_level})")
        fig.add_hline(y=put_wall, line_color="green", line_width=2, annotation_text=f"Put Wall ({put_wall})")
        fig.add_trace(go.Scatter(x=["Spot"], y=[spot], mode="markers+text", text=[f"{spot}"], marker=dict(color="cyan", size=18)))
        fig.update_layout(height=380, template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # Smooth Streamlit Auto-refresh without full page reload
        time.sleep(8)
        st.rerun()

else:
    st.info("👈 Left Sidebar mein apna **Upstox Access Token** paste karke **'Connect & Permanent Save'** dabaayein.")
