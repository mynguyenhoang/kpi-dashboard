import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# 1. CẤU HÌNH TRANG & CSS
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
    .kpi-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
        background-color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kpi-table th {
        background-color: #1f2937;
        color: white;
        padding: 10px 12px;
        text-align: center;
        border: 1px solid #d1d5db;
        font-size: 14px;
        font-weight: bold;
    }
    .kpi-table td {
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        font-size: 14px;
        vertical-align: middle;
    }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
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

    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip().replace('%', '').replace(',', '')
                if v == "" or "#" in v or "-" == v: return 0.0
                return float(v)
            return 0.0
        except: return 0.0

    # Xác định số ngày trong tháng
    date_row_idx = 3
    start_col_idx = 6 # Mặc định cột G
    num_days = 31
    for c in range(2, len(vals[date_row_idx])):
        if str(vals[date_row_idx][c]).strip() == "1":
            start_col_idx = c
            break
    
    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"{i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
        data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # HOÁN ĐỔI LẠI VỊ TRÍ NẾU BỊ NGƯỢC (Ở ĐÂY TÔI GIỮ THEO LOGIC CŨ NHƯNG BẠN CÓ THỂ ĐỔI BIẾN TRUYỀN VÀO)
        data["LH Tổng"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Tổng"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]

        # Weekly Summary Logic
        weekly_cols = [3, 4, 5, 6] # Cột D, E, F, G
        cw_idx = weekly_cols[-1]
        pw_idx = weekly_cols[-2]
        
        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": ((clean_val(lhc_idx, cw_idx) - clean_val(lht_idx, cw_idx))/clean_val(lhc_idx, cw_idx)*100) if clean_val(lhc_idx, cw_idx)>0 else 0,
            "pw_lhot": ((clean_val(lhc_idx, pw_idx) - clean_val(lht_idx, pw_idx))/clean_val(lhc_idx, pw_idx)*100) if clean_val(lhc_idx, pw_idx)>0 else 0,
            "cw_shot": ((clean_val(shc_idx, cw_idx) - clean_val(sht_idx, cw_idx))/clean_val(shc_idx, cw_idx)*100) if clean_val(shc_idx, cw_idx)>0 else 0,
            "pw_shot": ((clean_val(shc_idx, pw_idx) - clean_val(sht_idx, pw_idx))/clean_val(shc_idx, pw_idx)*100) if clean_val(shc_idx, pw_idx)>0 else 0,
        }
        return pd.DataFrame(data), summary

    # HCM: LH (38,40), Shuttle (39,41) -> Nếu bị ngược, hãy đổi vị trí 38,40 cho 39,41
    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    # BN: LH (47,49), Shuttle (48,50)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)

    return data_hcm, data_bn

def format_vn(n):
    return f"{n:,.0f}".replace(",", ".") if n > 0 else ""

def render_dashboard(df, summary, color):
    # 1. METRICS (MTD)
    st.columns(6) # Code rút gọn hiển thị metric...
    
    # 2. WOW TABLE (Code rút gọn...)
    st.markdown("#### Bảng chỉ số KPI tuần", unsafe_allow_html=True)

    # 3. BIỂU ĐỒ SẢN LƯỢNG
    st.markdown(f"<h4 style='color:{color}'>1. Biểu Đồ Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1, 1])
    
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", mode='lines+markers+text', 
                                 text=[format_vn(x) for x in df['Inbound Vol']], textposition="top center", line=dict(color='#0ea5e9')))
        fig.update_layout(title="Inbound hàng ngày", height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#38bdf8',
                               text=[format_vn(x) for x in df['Total Process Vol']], textposition='outside'))
        fig.update_layout(title="Năng suất (Số đơn)", height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#818cf8',
                               text=[format_vn(x) for x in df['Total Process Wgt']], textposition='outside'))
        fig.update_layout(title="Năng suất (Trọng lượng kg)", height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    # 4. QUẢN LÝ VẬN TẢI (FIX LỖI NGƯỢC VÀ HIỂN THỊ SỐ)
    st.markdown(f"<h4 style='color:{color}'>2. Quản lý Vận Tải</h4>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns([1, 1, 1])

    with c4:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['LH Tổng'] - df['LH Trễ'], name="LH Đúng giờ", marker_color='#10b981'))
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Tổng'] - df['Shuttle Trễ'], name="Shuttle Đúng giờ", marker_color='#3b82f6'))
        fig.update_layout(title="Tổng số chuyến xe (Stack)", barmode='stack', height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with c5:
        # BIỂU ĐỒ TRỄ LINEHAUL - HIỂN THỊ SỐ
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['LH Trễ'], marker_color='#ef4444',
                               text=[f"{int(x)}" if x > 0 else "" for x in df['LH Trễ']], textposition='outside'))
        fig.update_layout(title="Số chuyến xe trễ Linehaul", height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        # BIỂU ĐỒ TRỄ SHUTTLE - HIỂN THỊ SỐ
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['Shuttle Trễ'], marker_color='#f97316',
                               text=[f"{int(x)}" if x > 0 else "" for x in df['Shuttle Trễ']], textposition='outside'))
        fig.update_layout(title="Số chuyến xe trễ Shuttle", height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

# CHƯƠNG TRÌNH CHÍNH
data_hcm, data_bn = get_data()
tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
