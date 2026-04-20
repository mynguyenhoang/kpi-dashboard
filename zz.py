import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# =================================================================
# 1. CẤU HÌNH TRANG & CSS (GIỮ NGUYÊN GỐC)
# =================================================================
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>    .kpi-table {        width: 100%;        border-collapse: collapse;        margin-bottom: 30px;        background-color: white;        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;        box-shadow: 0 1px 3px rgba(0,0,0,0.1);    }    .kpi-table th {        background-color: #1f2937;        color: white;        padding: 10px 12px;        text-align: center;        border: 1px solid #d1d5db;        font-size: 14px;        font-weight: bold;        line-height: 1.4;    }    .kpi-table td {        padding: 10px 12px;        border: 1px solid #d1d5db;        font-size: 14px;        vertical-align: middle;        line-height: 1.4;    }    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }    .col-metric { font-weight: 600; color: #1e293b; }    .col-num { text-align: right; font-family: monospace; font-size: 15px; }    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }    div[data-testid="metric-container"] {        background-color: #ffffff;        border: 1px solid #e2e8f0;        padding: 15px 20px;        border-radius: 8px;        box-shadow: 0 2px 4px rgba(0,0,0,0.02);    }</style>""", unsafe_allow_html=True)

# =================================================================
# 2. LOGIC LẤY DỮ LIỆU TỪ FEISHU (GIỮ NGUYÊN TUYỆT ĐỐI)
# =================================================================
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
    if not token:
        st.error("Không lấy được Token Feishu.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    res_data = requests.get(url, headers=headers, timeout=30).json()
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    
    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v:                      
                    return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else 0.0
            return np.nan
        except: return np.nan

    start_col_idx = -1
    for c in range(2, len(vals[3])):
        if str(vals[3][c]).strip() == "1":
            start_col_idx = c
            break
    num_days = 26 
    if start_col_idx != -1:
        max_day = 1
        for c in range(start_col_idx, len(vals[3])):
            val = str(vals[3][c]).strip()
            if val.isdigit(): max_day = max(max_day, int(val))
        num_days = max_day
    else: start_col_idx = 6
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
        
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        lh_c_list = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_to_scan]
        sh_c_list = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_to_scan]
        data["LH Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(lh_c_list, data["LH Trễ"])]
        data["Shuttle Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(sh_c_list, data["Shuttle Trễ"])]
        
        valid_weeks = [idx for idx in [3, 4, 5, 6] if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1
        
        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            return ((chuyen - (0 if pd.isna(tre) else tre)) / chuyen) * 100
            
        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), summary

    return extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41), extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)

# =================================================================
# 3. GIAO DIỆN (ĐÃ ĐỔI TIÊU ĐỀ THEO YÊU CẦU)
# =================================================================
def format_vietnam(number):
    if pd.isna(number): return ""
    return f"{number:,.0f}".replace(",", ".")

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # 1. Metrics (MTD)
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(6)
    cols[0].metric("Inbound (MTD)", format_vietnam(df['Inbound Vol'].sum()))
    cols[1].metric("Outbound (MTD)", format_vietnam(df['Outbound Vol'].sum()))
    cols[2].metric("Xử lý (MTD)", format_vietnam(df['Total Process Vol'].sum()))
    cols[3].metric("Trọng lượng (MTD)", format_vietnam(df['Total Process Wgt'].sum()))
    cols[4].metric("Missort (MTD)", format_vietnam(df['Missort'].sum()))
    cols[5].metric("Backlog (MTD)", format_vietnam(df['Backlog'].sum()))

    # 2. Biểu đồ sản lượng & năng suất
    st.markdown(f"<h4 style='color: {primary_color};'>1. Biểu Đồ Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig.update_layout(title="Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig_v = px.bar(df, x='Ngày', y='Total Process Vol', title="Năng suất (Số đơn)", text=df['Total Process Vol'].apply(format_vietnam))
        fig_v.update_traces(marker_color='#38bdf8', textposition='outside')
        st.plotly_chart(fig_v, use_container_width=True)
    with c3:
        fig_w = px.bar(df, x='Ngày', y='Total Process Wgt', title="Năng suất (Trọng lượng kg)", text=df['Total Process Wgt'].apply(format_vietnam))
        fig_w.update_traces(marker_color='#818cf8', textposition='outside')
        st.plotly_chart(fig_w, use_container_width=True)

    # 3. QUẢN LÝ VẬN TẢI: ĐÃ ĐỔI TÊN TIÊU ĐỀ THEO CHỈ DẪN
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    col4, col5, col6 = st.columns([1, 1, 1])
    
    with col4:
        # Đã đổi tiêu đề thành Shuttle cho đúng cột dữ liệu trễ bên trái
        fig_lh = go.Figure()
        fig_lh.add_trace(go.Bar(
            x=df['Ngày'], 
            y=df['LH Trễ'], 
            marker_color='#f43f5e', 
            text=df['LH Trễ'].apply(lambda x: f"{int(x)}" if pd.notna(x) and x > 0 else ""), 
            textposition='outside'
        ))
        fig_lh.update_layout(title="Tổng chuyến Shuttle TRỄ", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_lh, use_container_width=True)

    with col5:
        # Đã đổi tiêu đề thành Linehaul cho đúng cột dữ liệu trễ bên phải
        fig_sh = go.Figure()
        fig_sh.add_trace(go.Bar(
            x=df['Ngày'], 
            y=df['Shuttle Trễ'], 
            marker_color='#f43f5e', 
            text=df['Shuttle Trễ'].apply(lambda x: f"{int(x)}" if pd.notna(x) and x > 0 else ""), 
            textposition='outside'
        ))
        fig_sh.update_layout(title="Tổng chuyến Linehaul TRỄ", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_sh, use_container_width=True)

    with col6:
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text=df['Backlog'].apply(lambda x: format_vietnam(x) if x > 0 else ""))
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        fig_bl.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_bl, use_container_width=True)

# Main App
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
t1, t2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with t1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with t2: render_dashboard(data_bn[0], data_bn[1], "#059669")
