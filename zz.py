import streamlit as st
import pandas as pd
import numpy as np
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
                if v == "" or "#" in v or v == "-": return 0.0
                return float(v)
            return 0.0
        except: return 0.0

    date_row_idx = 3
    start_col_idx = 6 # Cột G (Ngày 1)
    num_days = 31
    for c in range(2, len(vals[date_row_idx])):
        if str(vals[date_row_idx][c]).strip() == "1":
            start_col_idx = c
            break
    
    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
        data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # DỮ LIỆU VẬN TẢI
        data["LH Tổng"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Tổng"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]

        # Weekly Summary (WOW)
        weekly_cols = [3, 4, 5, 6] 
        cw = weekly_cols[-1]
        pw = weekly_cols[-2]
        
        def calc_ot(c_idx, t_idx, col):
            total = clean_val(c_idx, col)
            late = clean_val(t_idx, col)
            return ((total - late)/total*100) if total > 0 else 0

        summary = {
            "cw_vin": clean_val(vin_idx, cw), "pw_vin": clean_val(vin_idx, pw),
            "cw_vout": clean_val(vout_idx, cw), "pw_vout": clean_val(vout_idx, pw),
            "cw_ms": clean_val(ms_idx, cw), "pw_ms": clean_val(ms_idx, pw),
            "cw_bl": clean_val(bl_idx, cw), "pw_bl": clean_val(bl_idx, pw),
            "cw_lhot": calc_ot(lhc_idx, lht_idx, cw), "pw_lhot": calc_ot(lhc_idx, lht_idx, pw),
            "cw_shot": calc_ot(shc_idx, sht_idx, cw), "pw_shot": calc_ot(shc_idx, sht_idx, pw),
        }
        return pd.DataFrame(data), summary

    # HCM: LH(38,40), Shuttle(39,41) | BN: LH(47,49), Shuttle(48,50)
    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. HELPER FORMAT
def fmt(n):
    if n == 0 or pd.isna(n): return ""
    return f"{n:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev == 0: return f"<td style='text-align:center'>-</td><td class='col-num'>{'%.2f%%'%cur if is_pct else fmt(cur)}</td><td>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff/prev*100)
    color = "#15803d" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background:{bg};color:{color};font-weight:bold;text-align:center'>{sign}{pct:.1f}%</td><td class='col-num'>{'%.2f%%'%cur if is_pct else fmt(cur)}</td><td class='col-num'>{'%.2f%%'%prev if is_pct else fmt(prev)}</td>"

# 4. RENDER DASHBOARD
def render_dashboard(df, sum_data, color):
    # Metrics MTD
    t_vin, t_vout, t_ms, t_bl = df['Inbound Vol'].sum(), df['Outbound Vol'].sum(), df['Missort'].sum(), df['Backlog'].sum()
    lhot = (df['LH Tổng'].sum() - df['LH Trễ'].sum()) / df['LH Tổng'].sum() * 100 if df['LH Tổng'].sum() > 0 else 0
    shot = (df['Shuttle Tổng'].sum() - df['Shuttle Trễ'].sum()) / df['Shuttle Tổng'].sum() * 100 if df['Shuttle Tổng'].sum() > 0 else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound MTD", fmt(t_vin))
    c2.metric("Outbound MTD", fmt(t_vout))
    c3.metric("Process MTD", fmt(df['Total Process Vol'].sum()))
    c4.metric("Weight MTD", fmt(df['Total Process Wgt'].sum()))
    c5.metric("Missort MTD", fmt(t_ms))
    c6.metric("Backlog MTD", fmt(t_bl))

    # WOW TABLE
    st.markdown(f"""<table class='kpi-table'>
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style='width:100px'>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan='2' class='col-pillar' style='color:#0ea5e9'>Sản Lượng</td><td class='col-metric'>Inbound</td>{get_wow_cell(sum_data['cw_vin'], sum_data['pw_vin'])}<td class='col-mtd'>{fmt(t_vin)}</td></tr>
            <tr><td class='col-metric'>Outbound</td>{get_wow_cell(sum_data['cw_vout'], sum_data['pw_vout'])}<td class='col-mtd'>{fmt(t_vout)}</td></tr>
            <tr><td rowspan='2' class='col-pillar' style='color:#ef4444'>Chất Lượng</td><td class='col-metric'>Missort</td>{get_wow_cell(sum_data['cw_ms'], sum_data['pw_ms'], inverse=True)}<td class='col-mtd'>{fmt(t_ms)}</td></tr>
            <tr><td class='col-metric'>Backlog</td>{get_wow_cell(sum_data['cw_bl'], sum_data['pw_bl'], inverse=True)}<td class='col-mtd'>{fmt(t_bl)}</td></tr>
            <tr><td rowspan='2' class='col-pillar' style='color:#10b981'>Vận Tải</td><td class='col-metric'>LH On-time</td>{get_wow_cell(sum_data['cw_lhot'], sum_data['pw_lhot'], is_pct=True)}<td class='col-mtd'>{lhot:.2f}%</td></tr>
            <tr><td class='col-metric'>Shuttle On-time</td>{get_wow_cell(sum_data['cw_shot'], sum_data['pw_shot'], is_pct=True)}<td class='col-mtd'>{shot:.2f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # BIỂU ĐỒ 1: SẢN LƯỢNG
    st.markdown(f"<h4 style='color:{color}'>1. Biểu Đồ Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns([1.2, 1, 1])
    with g1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', mode='lines+markers+text', text=[fmt(x) for x in df['Inbound Vol']], textposition="top center"))
        fig.update_layout(title="Inbound Volume", height=350, plot_bgcolor='white', margin=dict(t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#38bdf8', text=[fmt(x) for x in df['Total Process Vol']], textposition='outside'))
        fig.update_layout(title="Năng suất (Đơn)", height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
    with g3:
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#818cf8', text=[fmt(x) for x in df['Total Process Wgt']], textposition='outside'))
        fig.update_layout(title="Năng suất (Kg)", height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    # BIỂU ĐỒ 2: VẬN TẢI (ĐÃ FIX HOÁN ĐỔI & HIỆN SỐ)
    st.markdown(f"<h4 style='color:{color}'>2. Quản lý Vận Tải</h4>", unsafe_allow_html=True)
    g4, g5, g6 = st.columns([1, 1, 1])
    with g4:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['LH Tổng'] - df['LH Trễ'], name="LH Đúng Giờ", marker_color='#10b981'))
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Tổng'] - df['Shuttle Trễ'], name="Shuttle Đúng Giờ", marker_color='#3b82f6'))
        fig.update_layout(title="Tổng chuyến xe", barmode='stack', height=350, plot_bgcolor='white', legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
     with g5:
        # Biểu đồ phải: Trễ Shuttle
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['Shuttle Trễ'], marker_color='#f97316', text=[fmt(x) for x in df['Shuttle Trễ']], textposition='outside'))
        fig.update_layout(title="Số chuyến xe trễ Shuttle", height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
    with g6:
        # Biểu đồ giữa: Trễ Linehaul
        fig = go.Figure(go.Bar(x=df['Ngày'], y=df['LH Trễ'], marker_color='#ef4444', text=[fmt(x) for x in df['LH Trễ']], textposition='outside'))
        fig.update_layout(title="Số chuyến xe trễ Linehaul", height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
   

# MAIN
st.markdown("<h2 style='text-align:center;color:#1e293b'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
if data_hcm[0].empty: 
    st.error("Không lấy được dữ liệu. Kiểm tra lại Feishu Token!")
else:
    t1, t2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
    with t1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
    with t2: render_dashboard(data_bn[0], data_bn[1], "#059669")
