import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px; text-align: center; border: 1px solid #d1d5db; }
    .kpi-table td { padding: 10px; border: 1px solid #d1d5db; text-align: center; }
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except: return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(r, c):
        try:
            v = str(vals[r][c]).strip().replace(',', '')
            return float(v) if v not in ["", "None", "-"] else 0.0
        except: return 0.0

    start_col = 6
    for c in range(2, len(vals[3])):
        if str(vals[3][c]).strip() == "1":
            start_col = c
            break
    
    num_days = 26
    cols = [start_col + i for i in range(num_days)]

    def extract(vin, vout, win, wout, tvol, twgt, ms, msr, bl, lhc, shc):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin, c) for c in cols]
        data["Outbound Vol"] = [clean_val(vout, c) for c in cols]
        data["Total Process Vol"] = [clean_val(tvol, c) for c in cols]
        data["Total Process Wgt"] = [clean_val(twgt, c) for c in cols]
        data["Missort"] = [clean_val(ms, c) for c in cols]
        data["Backlog"] = [clean_val(bl, c) for c in cols]
        # LẤY TỔNG SỐ CHUYẾN THEO TÊN GỐC TRONG FILE
        data["Shuttle"] = [clean_val(shc, c) for c in cols]
        data["Linehaul"] = [clean_val(lhc, c) for c in cols]
        
        summary = {"cv": clean_val(vin, 6), "pv": clean_val(vin, 5), "cm": clean_val(ms, 6), "pm": clean_val(ms, 5), "cb": clean_val(bl, 6), "pb": clean_val(bl, 5)}
        return pd.DataFrame(data), summary

    hcm, s_hcm = extract(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 39)
    bn, s_bn = extract(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 48)
    return (hcm, s_hcm), (bn, s_bn)

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; font-weight: 800;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()

def render_dashboard(df, summary, primary_color):
    # Metrics
    c = st.columns(6)
    c[0].metric("Inbound MTD", f"{df['Inbound Vol'].sum():,.0f}")
    c[1].metric("Outbound MTD", f"{df['Outbound Vol'].sum():,.0f}")
    c[2].metric("Missort MTD", f"{df['Missort'].sum():,.0f}")
    c[3].metric("Backlog", f"{df['Backlog'].iloc[-1]:,.0f}")
    c[4].metric("Tổng Shuttle", f"{df['Shuttle'].sum():,.0f}")
    c[5].metric("Tổng Linehaul", f"{df['Linehaul'].sum():,.0f}")

    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # BIỂU ĐỒ GỘP TỔNG CHUYẾN (SHUTTLE + LINEHAUL)
        df_clean = df.copy().fillna(0)
        df_clean['Total_Trips'] = df_clean['Shuttle'] + df_clean['Linehaul']
        
        fig = go.Figure()
        # Cột Shuttle
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle'], name="Shuttle", 
                             marker_color='#3b82f6', text=df['Shuttle'], textposition='inside'))
        # Cột Linehaul
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['Linehaul'], name="Linehaul", 
                             marker_color='#10b981', text=df['Linehaul'], textposition='inside'))
        # Trace tàng hình để hiện con số TỔNG lên đầu cột
        fig.add_trace(go.Bar(x=df_clean['Ngày'], y=df_clean['Total_Trips'], name="Tổng",
                             marker_color='rgba(0,0,0,0)', hoverinfo='none', showlegend=False,
                             text=df_clean['Total_Trips'].apply(lambda x: int(x) if x > 0 else ""),
                             textposition='outside'))

        fig.update_layout(title="Tổng số chuyến xe (Shuttle & Linehaul)", barmode='stack', 
                          plot_bgcolor='white', height=450, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # BIỂU ĐỒ BACKLOG
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text_auto=True)
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        fig_bl.update_layout(plot_bgcolor='white', height=450)
        st.plotly_chart(fig_bl, use_container_width=True)

    # Năng suất & Sản lượng (Giữ nguyên cho đủ bộ)
    st.markdown("#### Sản lượng & Năng suất")
    st.line_chart(df.set_index("Ngày")[["Inbound Vol", "Outbound Vol"]])

if not data_hcm[0].empty:
    tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
    with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
    with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
