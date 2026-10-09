import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import requests
import time
from datetime import datetime

lo
st.set_page_config(page_title="Nifty Complete Smart Scalper Engine", layout="wide")

# Session State for Target/SL Lock
if 'locked_signal' not in st.session_state:
    st.session_state.locked_signal = "NEUTRAL"
if 'locked_entry' not in st.session_state:
    st.session_state.locked_entry = None
if 'locked_sl' not in st.session_state
