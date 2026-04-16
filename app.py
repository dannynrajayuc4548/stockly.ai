import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stockly.AI",
    page_icon="📈",
    layout="wide",  # changed from 'centered' — more room for charts
    initial_sidebar_state="collapsed",  # personal pref: start with sidebar hidden
)

# ── CSS — Claude.ai dark aesthetic ───────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: #1e1e1e !important;
    font-family: 'Inter', sans-serif !important;
    color: #ececec !important;
}

#MainMenu, footer { visibility: hidden; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stMainBlockContainer"] {
    padding: 28px 36px 120px 36px !important;
    max-width: 960px !important;  /* widened slightly for better chart readability */
    margin: 0 auto !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background-color: #171717 !important;
    border-right: 1px solid #2a2a2a !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    color: #9a9a9a !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: #1e1e1e !important;
    border: 1px solid #2e2e2e !important;
    border-radius: 8px !important;
    color: #d4d4d4 !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] .stRadio > div > label {
    background-color: transparent !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 7px !important;
    padding: 8px 12px !important;
    color: #8a8a8a !important;
    font-size: 12.5px !important;
    width: 100% !important;
    cursor: pointer !important;
    transition: background 0.12s !important;
    margin-bottom: 3px !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    background-color: #232323 !important;
    color: #d4d4d4 !important;
}
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
    background-color: #252525 !important;
    border-color: #4a4a4a !important;
    color: #ececec !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background-color: transparent !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 7px !important;
    color: #8a8a8a !important;
    font-size: 12.5px !important;
    padding: 8px 13px !important;
    width: 100% !important;
    text-align: left !important;
    margin-bottom: 4px !important;
    transition: background 0.12s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #232323 !important;
    color: #d4d