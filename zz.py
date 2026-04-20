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
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; line-height: 1.4; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; line-height: 1.4; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
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
    max_retries = 3
    res_data = None
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            time.sleep(2)
        except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except: return np.nan

    date_row_idx = 3
    start_col_idx = -1
    for c in range(2, len(vals[date_row_idx])):
        if str(vals[date_row_idx][c]).strip() == "1":
            start_col_idx = c
            break
    num_days = 26
    if start_col_idx != -1:
        max_day = 1
        for c in range(start_col_idx, len(vals[date_row_idx])):
            val = str(vals[date_row_idx][c]).strip()
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
        
        # Lấy TỔNG CHUYẾN XE (Gốc từ Feishu)
        data["Linehaul_Total"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle_Total"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        # Tính Đúng Giờ phục vụ bảng KPI
        data["LH Đúng Giờ"] = [(c - t) if (pd.notna(c) and pd.notna(t)) else np.nan for c, t in zip(data["Linehaul_Total"], data["LH Trễ"])]
        data["Shuttle Đúng Giờ"] = [(c - t) if (pd.notna(c) and pd.notna(t)) else np.nan for c, t in zip(data["Shuttle_Total"], data["Shuttle Trễ"])]

        valid_weeks = [3, 4, 5, 6]
        cw_idx = -1
        for idx in valid_weeks:
            if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0: cw_idx = idx
        pw_idx = valid_weeks[valid_weeks.index(cw_idx)-1] if cw_idx in valid_weeks and valid_weeks.index(cw_idx) > 0 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            return ((chuyen - (0 if pd.isna(tre) else tre)) / chuyen) * 100

        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), weekly_summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu...")
    st.stop()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vn(n):
    return f"{n:,.0f}".replace(",", ".") if pd.notna(n) else ""

def render_dashboard(df, summary, primary_color):
    # Metrics MTD
    st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>KPI DASHBOARD</h2>", unsafe_allow_html=True)
    c = st.columns(6)
    m_list = [("Inbound", df['Inbound Vol'].sum()), ("Outbound", df['Outbound Vol'].sum()), ("Xử lý", df['Total Process Vol'].sum()), ("Trọng lượng", df['Total Process Wgt'].sum()), ("Missort", df['Missort'].sum()), ("Backlog", df['Backlog'].sum())]
    for col, (l, v) in zip(c, m_list): col.metric(f"{l} (MTD)", format_vn(v))

    # Bảng KPI WOW (Tự động cập nhật từ logic gốc)
    # ... (Phần bảng WOW giữ nguyên như code trước của bạn)

    # 1. BIỂU ĐỒ SẢN LƯỢNG
    st.markdown(f"#### 1. Biểu Đồ Sản Lượng & Năng Suất")
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig.update_layout(title="Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)
    with c2: st.plotly_chart(px.bar(df, x='Ngày', y='Total Process Vol', title="Năng suất (Số đơn)", text_auto='.2s').update_layout(plot_bgcolor='white'), use_container_width=True)
    with c3: st.plotly_chart(px.bar(df, x='Ngày', y='Total Process Wgt', title="Năng suất (Kg)", text_auto='.2s').update_layout(plot_bgcolor='white'), use_container_width=True)

    # 2. QUẢN LÝ VẬN TẢI (SỬA THEO YÊU CẦU: CHỈ HIỂN THỊ TỔNG CHUYẾN XE)
    st.markdown(f"#### 2. Quản lý Vận Tải & Hàng Tồn")
    
    # Biểu đồ Tổng số chuyến xe trong ngày (LH vs Shuttle)
    fig_total = go.Figure()
    fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['Linehaul_Total'], name="Linehaul", marker_color='#10b981', text=df['Linehaul_Total'], textposition='outside'))
    fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle_Total'], name="Shuttle", marker_color='#3b82f6', text=df['Shuttle_Total'], textposition='outside'))
    fig_total.update_layout(title="Tổng số chuyến xe phát sinh trong ngày (LH vs Shuttle)", barmode='group', plot_bgcolor='white', height=400, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_total, use_container_width=True)

    # 3. CHI TIẾT TRỄ & BACKLOG
    c_t1, c_t2, c_bl = st.columns(3)
    with c_t1:
        st.plotly_chart(px.bar(df, x='Ngày', y='LH Trễ', title="Tổng chuyến Linehaul TRỄ", text_auto=True).update_traces(marker_color='#ef4444').update_layout(plot_bgcolor='white', height=300), use_container_width=True)
    with c_t2:
        st.plotly_chart(px.bar(df, x='Ngày', y='Shuttle Trễ', title="Tổng chuyến Shuttle TRỄ", text_auto=True).update_traces(marker_color='#f43f5e').update_layout(plot_bgcolor='white', height=300), use_container_width=True)
    with c_bl:
        st.plotly_chart(px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text_auto=True).update_traces(marker_color='#f59e0b').update_layout(plot_bgcolor='white', height=300), use_container_width=True)

with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
