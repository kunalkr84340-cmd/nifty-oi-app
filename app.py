import streamlit as st
import plotly.graph_objects as go
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Nifty Complete Smart Scalper Engine", layout="wide")

query_params = st.query_params
current_token = query_params.get("token", "")

st.sidebar.header("⚙️ Upstox API Connection")
input_token = st.sidebar.text_input("🔑 Upstox Access Token Paste Karein", value=current_token, type="password")

if st.sidebar.button("Connect & Save"):
    if input_token:
        st.query_params["token"] = input_token
        st.sidebar.success("✅ Token Saved!")
        st.rerun()

active_token = query_params.get("token", "")

st.title("🎯 Nifty Live Smart Dynamic Analyst & Candle Engine")

@st.cache_data(ttl=5)
def fetch_complete_market_data(token):
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

        # 2. Fetch Live Candles (5 Min Interval)
        to_date = datetime.now().strftime("%Y-%m-%d")
        candle_url = f"https://api.upstox.com/v2/historical-candle/NSE_INDEX|Nifty 50/minute/5/{to_date}"
        candle_res = requests.get(candle_url, headers=headers).json()
        candles = candle_res.get('data', {}).get('candles', [])

        # 3. Fetch Option Chain for Detailed OI Analysis
        contracts_url = "https://api.upstox.com/v2/option/contract?instrument_key=NSE_INDEX|Nifty 50"
        contracts_res = requests.get(contracts_url, headers=headers).json()
        expiries = sorted(list(set([x.get('expiry') for x in contracts_res.get('data', []) if x.get('expiry')])))
        
        nearest_expiry = expiries[0] if expiries else None
        
        call_pct_map, put_pct_map = {}, {}
        call_oi_map, put_oi_map = {}, {}
        
        if nearest_expiry:
            chain_url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={nearest_expiry}"
            chain_res = requests.get(chain_url, headers=headers).json()
            
            for item in chain_res.get('data', []):
                strike = item.get('strike_price', 0)
                if abs(strike - spot_price) <= 400:
                    # Call Processing
                    c_opts = item.get('call_options', {})
                    if c_opts:
                        c_mkt = c_opts.get('market_data', {})
                        c_oi = c_mkt.get('oi', 0)
                        call_oi_map[strike] = c_oi
                        c_pct = c_mkt.get('p_change', 0.0)
                        if not c_pct or c_pct == 0:
                            prev = c_mkt.get('prev_oi', 1)
                            if prev > 0: c_pct = ((c_oi - prev)/prev)*100
                        call_pct_map[strike] = round(float(c_pct), 1)
                        
                    # Put Processing
                    p_opts = item.get('put_options', {})
                    if p_opts:
                        p_mkt = p_opts.get('market_data', {})
                        p_oi = p_mkt.get('oi', 0)
                        put_oi_map[strike] = p_oi
                        p_pct = p_mkt.get('p_change', 0.0)
                        if not p_pct or p_pct == 0:
                            prev = p_mkt.get('prev_oi', 1)
                            if prev > 0: p_pct = ((p_oi - prev)/prev)*100
                        put_pct_map[strike] = round(float(p_pct), 1)

        top_calls = sorted(call_pct_map.items(), key=lambda x: x[1], reverse=True)[:3]
        top_puts = sorted(put_pct_map.items(), key=lambda x: x[1], reverse=True)[:3]
        
        max_call_wall = max(call_oi_map, key=call_oi_map.get) if call_oi_map else spot_price + 100
        max_put_wall = max(put_oi_map, key=put_oi_map.get) if put_oi_map else spot_price - 100

        return {
            "spot": spot_price,
            "candles": candles,
            "top_calls": top_calls,
            "top_puts": top_puts,
            "max_call_wall": max_call_wall,
            "max_put_wall": max_put_wall
        }, None

    except Exception as e:
        return None, str(e)

# --- App Execution ---
if active_token:
    data, err = fetch_complete_market_data(active_token)
    
    if err:
        st.error(f"⚠️ Status: {err}")
        st.info("💡 Token Expire hone par naya Token Paste karein.")
        if st.button("Reset Saved Token"):
            st.query_params.clear()
            st.rerun()
    else:
        spot = data['spot']
        candles = data['candles']
        top_calls = data['top_calls']
        top_puts = data['top_puts']
        call_wall = data['max_call_wall']
        put_wall = data['max_put_wall']
        
        pivot_level = (call_wall + put_wall) / 2
        tot_call_pct = sum([v for k, v in top_calls])
        tot_put_pct = sum([v for k, v in top_puts])
        
        st.success(f"⚡ Live Connected! Nifty Spot Price: **{spot}**")
        
        # Metrics Display
        m1, m2, m3 = st.columns(3)
        m1.metric("Major Call Resistance", f"{call_wall}")
        m2.metric("Calculated Pivot Level", f"{pivot_level}")
        m3.metric("Major Put Support", f"{put_wall}")
        
        st.markdown("---")
        st.subheader("📊 Dynamic Market Observation & Deep Analysis")
        
        call_build_str = ", ".join([f"**{k} CE (+{v}%)**" for k, v in top_calls])
        put_build_str = ", ".join([f"**{k} PE (+{v}%)**" for k, v in top_puts])
        
        # Target/SL & Trade Direction Calculation
        signal = "NEUTRAL"
        entry_price, sl_price, target_price = None, None, None
        
        if tot_call_pct > tot_put_pct * 1.3:
            signal = "BEARISH (PUT BUY)"
            entry_price = spot
            sl_price = round(spot + 35, 2)
            target_price = round(spot - 70, 2)
            
            st.error(
                f"🔴 **Call Writing Heavy Dynamic Shift Detected:**\n"
                f"• Call side par aggressive build-up ho gaya hai: {call_build_str}.\n"
                f"• Above levels completely block ho rahe hain aur market par **Bearish Pressure** haavi hai."
            )
        elif tot_put_pct > tot_call_pct * 1.3:
            signal = "BULLISH (CALL BUY)"
            entry_price = spot
            sl_price = round(spot - 35, 2)
            target_price = round(spot + 70, 2)
            
            st.success(
                f"🟢 **Put Writing Strong Dynamic Shift Detected:**\n"
                f"• Put side par aggressive build-up ho raha hai: {put_build_str}.\n"
                f"• Lower levels par strong support mil raha hai aur market par **Bullish Momentum** haavi hai."
            )
        else:
            st.warning("⚠️ **Rangebound / Neutral Pressure:** Call aur Put dono side barabar spikings hain. Wait for break.")

        # Scalp Guidance Strategy
        st.subheader("🎯 Action Plan & Trade Levels")
        if entry_price:
            c1, c2, c3 = st.columns(3)
            c1.info(f"📍 **Entry Price Zone:** {entry_price}")
            c2.error(f"🛑 **Stop-Loss Level:** {sl_price}")
            c3.success(f"🎯 **Target Level:** {target_price}")

        # Candlestick Chart Rendering
        if candles:
            st.subheader("📈 Live 5-Min Candlestick Chart")
            times = [c[0] for c in candles[:30]][::-1]
            opens = [c[1] for c in candles[:30]][::-1]
            highs = [c[2] for c in candles[:30]][::-1]
            lows = [c[3] for c in candles[:30]][::-1]
            closes = [c[4] for c in candles[:30]][::-1]

            fig = go.Figure(data=[go.Candlestick(
                x=times,
                open=opens, high=highs,
                low=lows, close=closes,
                name="Nifty 5M"
            )])

            # Target, SL, and Entry Lines
            if signal != "NEUTRAL":
                fig.add_hline(y=entry_price, line_color="cyan", line_dash="dash", annotation_text=f"ENTRY ({entry_price})")
                fig.add_hline(y=sl_price, line_color="red", line_width=2, annotation_text=f"STOP LOSS ({sl_price})")
                fig.add_hline(y=target_price, line_color="green", line_width=2, annotation_text=f"TARGET ({target_price})")
            
            fig.update_layout(
                height=450,
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

        # Smooth Auto-Refresh Background Update
        time.sleep(8)
        st.rerun()

else:
    st.info("👈 Left Sidebar mein apna **Upstox Access Token** paste karke **'Connect & Save'** dabaayein.")
        
