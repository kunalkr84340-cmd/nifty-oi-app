import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Nifty Smart Scalper & Signal Tracker Engine", layout="wide")

# Initialize Session State for Fixed Target/SL Lock & Signal Tracker
if 'locked_signal' not in st.session_state:
    st.session_state.locked_signal = "NEUTRAL"
if 'locked_entry' not in st.session_state:
    st.session_state.locked_entry = None
if 'locked_sl' not in st.session_state:
    st.session_state.locked_sl = None
if 'locked_target' not in st.session_state:
    st.session_state.locked_target = None
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []

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

st.title("🎯 Nifty Live Smart Scalper & Signal Tracker Engine")

@st.cache_data(ttl=3)
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

        # 2. Fetch Live Candles
        today_date = datetime.now().strftime("%Y-%m-%d")
        candle_url = f"https://api.upstox.com/v2/historical-candle/NSE_INDEX|Nifty 50/minute/5/{today_date}"
        candle_res = requests.get(candle_url, headers=headers).json()
        candles = candle_res.get('data', {}).get('candles', [])

        # 3. Fetch Option Chain
        contracts_url = "https://api.upstox.com/v2/option/contract?instrument_key=NSE_INDEX|Nifty 50"
        contracts_res = requests.get(contracts_url, headers=headers).json()
        expiries = sorted(list(set([x.get('expiry') for x in contracts_res.get('data', []) if x.get('expiry')])))
        
        nearest_expiry = expiries[0] if expiries else None
        
        call_pct_map, put_pct_map = {}, {}
        call_oi_map, put_oi_map = {}, {}
        table_data = []
        
        if nearest_expiry:
            chain_url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty 50&expiry_date={nearest_expiry}"
            chain_res = requests.get(chain_url, headers=headers).json()
            
            for item in chain_res.get('data', []):
                strike = item.get('strike_price', 0)
                if abs(strike - spot_price) <= 250:
                    c_opts = item.get('call_options', {})
                    if c_opts:
                        c_mkt = c_opts.get('market_data', {})
                        c_oi = c_mkt.get('oi', 0)
                        call_oi_map[strike] = c_oi
                        c_pct = c_mkt.get('p_change', 0.0)
                        if not c_pct or c_pct == 0:
                            prev = c_mkt.get('prev_oi', 1)
                            if prev > 0:
                                c_pct = ((c_oi - prev)/prev)*100
                        call_pct_map[strike] = round(float(c_pct), 1)
                        
                    p_opts = item.get('put_options', {})
                    if p_opts:
                        p_mkt = p_opts.get('market_data', {})
                        p_oi = p_mkt.get('oi', 0)
                        put_oi_map[strike] = p_oi
                        p_pct = p_mkt.get('p_change', 0.0)
                        if not p_pct or p_pct == 0:
                            prev = p_mkt.get('prev_oi', 1)
                            if prev > 0:
                                p_pct = ((p_oi - prev)/prev)*100
                        put_pct_map[strike] = round(float(p_pct), 1)

                    table_data.append({
                        "Call OI Change %": f"+{call_pct_map.get(strike, 0)}%",
                        "Call Total OI": call_oi_map.get(strike, 0),
                        "Strike Price": strike,
                        "Put Total OI": put_oi_map.get(strike, 0),
                        "Put OI Change %": f"+{put_pct_map.get(strike, 0)}%"
                    })

        top_calls = sorted(call_pct_map.items(), key=lambda x: x[1], reverse=True)[:5]
        top_puts = sorted(put_pct_map.items(), key=lambda x: x[1], reverse=True)[:5]
        
        max_call_wall = max(call_oi_map, key=call_oi_map.get) if call_oi_map else spot_price + 100
        max_put_wall = max(put_oi_map, key=put_oi_map.get) if put_oi_map else spot_price - 100

        return {
            "spot": spot_price,
            "candles": candles,
            "top_calls": top_calls,
            "top_puts": top_puts,
            "max_call_wall": max_call_wall,
            "max_put_wall": max_put_wall,
            "table_df": pd.DataFrame(table_data)
        }, None

    except Exception as e:
        return None, str(e)

# --- App Render ---
if active_token:
    data, err = fetch_complete_market_data(active_token)
    
    if err:
        st.error(f"⚠️ Status: {err}")
    else:
        spot = data['spot']
        candles = data['candles']
        top_calls = data['top_calls']
        top_puts = data['top_puts']
        call_wall = data['max_call_wall']
        put_wall = data['max_put_wall']
        df = data['table_df']
        
        pivot_level = (call_wall + put_wall) / 2
        tot_call_pct = sum([v for k, v in top_calls])
        tot_put_pct = sum([v for k, v in top_puts])
        
        st.success(f"⚡ Live Connected! Nifty Spot Price: **{spot}**")
        
        # Performance Tracker Banner
        history = st.session_state.trade_history
        total_trades = len(history)
        targets_hit = len([t for t in history if t['Status'] == 'TARGET HIT 🎯'])
        sl_hit = len([t for t in history if t['Status'] == 'SL HIT 🛑'])
        win_rate = round((targets_hit / total_trades) * 100, 1) if total_trades > 0 else 0.0

        st.subheader("📊 Live Signal Performance Scorecard")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Total Signals Generated", f"{total_trades}")
        p2.metric("Targets Hit (Wins)", f"{targets_hit}", delta=f"{targets_hit} Wins", delta_color="normal")
        p3.metric("SL Hit (Losses)", f"{sl_hit}", delta=f"-{sl_hit} SL", delta_color="inverse")
        p4.metric("Strategy Win Rate", f"{win_rate}%")

        st.markdown("---")

        # Live Auto Check Active Trade Status
        if st.session_state.locked_signal != "NEUTRAL":
            sig = st.session_state.locked_signal
            entry = st.session_state.locked_entry
            target = st.session_state.locked_target
            sl = st.session_state.locked_sl
            
            status_result = None
            if sig == "BULLISH (CALL BUY)":
                if spot >= target:
                    status_result = "TARGET HIT 🎯"
                elif spot <= sl:
                    status_result = "SL HIT 🛑"
            elif sig == "BEARISH (PUT BUY)":
                if spot <= target:
                    status_result = "TARGET HIT 🎯"
                elif spot >= sl:
                    status_result = "SL HIT 🛑"

            if status_result:
                st.session_state.trade_history.append({
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Type": sig,
                    "Entry": entry,
                    "Target": target,
                    "SL": sl,
                    "Status": status_result
                })
                st.session_state.locked_signal = "NEUTRAL"
                st.rerun()

        # Signal Logic & Locking
        if tot_call_pct > tot_put_pct * 1.3:
            if st.session_state.locked_signal == "NEUTRAL":
                st.session_state.locked_signal = "BEARISH (PUT BUY)"
                st.session_state.locked_entry = spot
                st.session_state.locked_sl = round(spot + 35, 2)
                st.session_state.locked_target = round(spot - 70, 2)
            st.error("🔴 **Call Writing Heavy Dynamic Shift Detected:** Bearish Pressure haavi hai.")
        elif tot_put_pct > tot_call_pct * 1.3:
            if st.session_state.locked_signal == "NEUTRAL":
                st.session_state.locked_signal = "BULLISH (CALL BUY)"
                st.session_state.locked_entry = spot
                st.session_state.locked_sl = round(spot - 35, 2)
                st.session_state.locked_target = round(spot + 70, 2)
            st.success("🟢 **Put Writing Strong Dynamic Shift Detected:** Bullish Momentum haavi hai.")
        else:
            st.warning("⚠️ **Rangebound / Neutral Pressure:** Wait for break.")

        # Action Plan Status
        st.subheader("🎯 Active Trade Status")
        if st.session_state.locked_signal != "NEUTRAL":
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"📍 **Locked Entry:** {st.session_state.locked_entry}")
            c2.error(f"🛑 **Fixed SL:** {st.session_state.locked_sl}")
            c3.success(f"🎯 **Fixed Target:** {st.session_state.locked_target}")
            if c4.button("Reset / Skip Trade"):
                st.session_state.locked_signal = "NEUTRAL"
                st.rerun()

        # History Table Display
        if history:
            st.subheader("📝 Today's Completed Signal Journal")
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)

        st.markdown("---")
        
        # Top Spikes & Option Chain Table
        st.subheader("🔥 Top 5 Live OI Spikes (Calls vs Puts)")
        call_build_str = "\n".join([f"• **{k} CE**: +{v}%" for k, v in top_calls])
        put_build_str = "\n".join([f"• **{k} PE**: +{v}%" for k, v in top_puts])
        
        col_call, col_put = st.columns(2)
        with col_call:
            st.error(f"🔴 **Top 5 Call OI Build-ups:**\n\n{call_build_str}")
        with col_put:
            st.success(f"🟢 **Top 5 Put OI Build-ups:**\n\n{put_build_str}")

        st.markdown("---")
        st.subheader("📋 ATM Option Chain Overview")
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Candlestick Chart
        st.subheader("📈 Live 5-Min Candlestick Chart")
        if candles:
            times = [c[0] for c in candles[:30]][::-1]
            opens = [c[1] for c in candles[:30]][::-1]
            highs = [c[2] for c in candles[:30]][::-1]
            lows = [c[3] for c in candles[:30]][::-1]
            closes = [c[4] for c in candles[:30]][::-1]

            fig = go.Figure(data=[go.Candlestick(x=times, open=opens, high=highs, low=lows, close=closes, name="Nifty 5M")])

            if st.session_state.locked_signal != "NEUTRAL":
                fig.add_hline(y=st.session_state.locked_entry, line_color="cyan", line_dash="dash", annotation_text=f"ENTRY ({st.session_state.locked_entry})")
                fig.add_hline(y=st.session_state.locked_sl, line_color="red", line_width=2, annotation_text=f"STOP LOSS ({st.session_state.locked_sl})")
                fig.add_hline(y=st.session_state.locked_target, line_color="green", line_width=2, annotation_text=f"TARGET ({st.session_state.locked_target})")
            
            fig.update_layout(height=480, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        time.sleep(8)
        st.rerun()

else:
    st.info("👈 Left Sidebar mein apna Upstox Access Token paste karke Connect karein.")
