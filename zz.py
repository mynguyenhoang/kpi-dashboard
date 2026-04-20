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
st.markdown("""<style>    .kpi-table {        width: 100%;        border-collapse: collapse;        margin-bottom: 30px;        background-color: white;        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;        box-shadow: 0 1px 3px rgba(0,0,0,0.1);    }    .kpi-table th {        background-color: #1f2937;        color: white;        padding: 10px 12px;        text-align: center;        border: 1px solid #d1d5db;        font-size: 14px;        font-weight: bold;        line-height: 1.4;    }    .kpi-table td {        padding: 10px 12px;        border: 1px solid #d1d5db;        font-size: 14px;        vertical-align: middle;        line-height: 1.4;    }    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }    .col-metric { font-weight: 600; color: #1e293b; }    .col-num { text-align: right; font-family: monospace; font-size: 15px; }    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }    div[data-testid="metric-container"] {        background-color: #ffffff;        border: 1px solid #e2e8f0;        padding: 15px 20px;        border-radius: 8px;        box-shadow: 0 2px 4px rgba(0,0,0,0.02);    }</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": "cli_a9456e412bb89bce", 
            "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except:
        return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token Feishu.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    max_retries = 3
    res_data = None
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            elif "not ready" in str(res.get("msg")).lower():
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        except Exception as e:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    if not res_data:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v:
                      return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except:
            return np.nan

    date_row_idx = 3 
    start_col_idx = -1
    for c in range(2, len(vals[date_row_idx])):
        val = str(vals[date_row_idx][c]).strip()
        if val == "1":
            start_col_idx = c
            break
    
    num_days = 26 
    if start_col_idx != -1:
        max_day = 1
        for c in range(start_col_idx, len(vals[date_row_idx])):
            val = str(vals[date_row_idx][c]).strip()
            if val.isdigit():
                max_day = max(max_day, int(val))
        num_days = max_day
    else:
        start_col_idx = 6
    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
        data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # Lấy trực tiếp số chuyến xe từ bảng (lh_c_list và sh_c_list)
        data["LH Chuyến"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["SH Chuyến"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        
        weekly_col_idxs = [3, 4, 5, 6]
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1
        
        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx)
        }
        return pd.DataFrame(data), weekly_summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # METRICS
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound (MTD)", format_vietnam(df['Inbound Vol'].sum()))
    c2.metric("Outbound (MTD)", format_vietnam(df['Outbound Vol'].sum()))
    c3.metric("Xử lý (MTD)", format_vietnam(df['Total Process Vol'].sum()))
    c4.metric("Trọng lượng (MTD)", format_vietnam(df['Total Process Wgt'].sum()))
    c5.metric("Missort (MTD)", format_vietnam(df['Missort'].sum()))
    c6.metric("Backlog", format_vietnam(df['Backlog'].iloc[-1] if not df['Backlog'].dropna().empty else 0))
    
    st.markdown("<br>", unsafe_allow_html=True)

    # BIỂU ĐỒ SẢN LƯỢNG
    st.markdown(f"<h4 style='color: {primary_color};'>1. Sản Lượng Hàng Ngày</h4>", unsafe_allow_html=True)
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", line=dict(color='#0ea5e9')))
    fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
    fig_vol.update_layout(plot_bgcolor='white', height=350, margin=dict(t=10, b=10))
    st.plotly_chart(fig_vol, use_container_width=True)

    # BIỂU ĐỒ VẬN TẢI & BACKLOG (YÊU CẦU CỦA BẠN)
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Linehaul: Cột xanh, hiện số chuyến lên đầu
        fig_lh = px.bar(df, x='Ngày', y='LH Chuyến', title="Linehaul (LH)", text_auto=True)
        fig_lh.update_traces(marker_color='#10b981', textposition='outside')
        fig_lh.update_layout(plot_bgcolor='white', yaxis_title="Số chuyến")
        st.plotly_chart(fig_lh, use_container_width=True)

    with col2:
        # Shuttle: Cột xanh dương, hiện số chuyến lên đầu
        fig_sh = px.bar(df, x='Ngày', y='SH Chuyến', title="Shuttle (ST)", text_auto=True)
        fig_sh.update_traces(marker_color='#3b82f6', textposition='outside')
        fig_sh.update_layout(plot_bgcolor='white', yaxis_title="Số chuyến")
        st.plotly_chart(fig_sh, use_container_width=True)

    with col3:
        # Backlog
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text_auto=True)
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        fig_bl.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_bl, use_container_width=True)

if not data_hcm[0].empty:
    tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
    with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
    with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
