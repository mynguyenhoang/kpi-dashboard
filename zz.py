import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# =================================================================
# 1. CẤU HÌNH TRANG & CSS (GIỮ NGUYÊN)
# =================================================================
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
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
        line-height: 1.4;
    }
    .kpi-table td {
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        font-size: 14px;
        vertical-align: middle;
        line-height: 1.4;
    }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGIC LẤY DỮ LIỆU (GIỮ NGUYÊN LOGIC CỦA BẠN)
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
    if not token: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers, timeout=30).json()
    vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    
    if not vals or len(vals) < 50: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip()
                if v == "" or "#" in v or "=" in v: return np.nan
                s = v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else 0.0
            return np.nan
        except: return np.nan

    # Xác định số ngày trong tháng
    start_col_idx = 6
    for c in range(2, len(vals[3])):
        if str(vals[3][c]).strip() == "1":
            start_col_idx = c
            break
    
    # Tìm ngày cuối cùng có dữ liệu (max_day)
    max_day = 1
    for c in range(start_col_idx, len(vals[3])):
        v = str(vals[3][c]).strip()
        if v.isdigit(): max_day = max(max_day, int(v))
    
    cols_to_scan = [start_col_idx + i for i in range(max_day)]

    def extract_hub_data(vin, vout, win, wout, tpv, tpw, ms, msr, bl, lhc, lht, shc, sht):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(max_day)]}
        data["Inbound Vol"] = [clean_val(vin, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout, c) for c in cols_to_scan]
        data["Total Process Vol"] = [clean_val(tpv, c) for c in cols_to_scan]
        data["Total Process Wgt"] = [clean_val(tpw, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl, c) for c in cols_to_scan]
        
        # Vận tải
        lh_c = [clean_val(lhc, c) or 0 for c in cols_to_scan]
        lh_t = [clean_val(lht, c) or 0 for c in cols_to_scan]
        sh_c = [clean_val(shc, c) or 0 for c in cols_to_scan]
        sh_t = [clean_val(sht, c) or 0 for c in cols_to_scan]
        
        data["LH Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = [t if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["Shuttle Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = [t if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]

        # Lấy tuần hiện tại (CW) và tuần trước (PW) - Cột 3,4,5,6
        valid_weeks = [idx for idx in [3, 4, 5, 6] if pd.notna(clean_val(vin, idx)) and clean_val(vin, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            return ((chuyen - (tre or 0)) / chuyen * 100) if chuyen and chuyen > 0 else 0

        summary = {
            "cw_vin": clean_val(vin, cw_idx), "pw_vin": clean_val(vin, pw_idx),
            "cw_vout": clean_val(vout, cw_idx), "pw_vout": clean_val(vout, pw_idx),
            "cw_ms": clean_val(ms, cw_idx), "pw_ms": clean_val(ms, pw_idx),
            "cw_bl": clean_val(bl, cw_idx), "pw_bl": clean_val(bl, pw_idx),
            "cw_lhot": get_ot_rate(lhc, lht, cw_idx), "pw_lhot": get_ot_rate(lhc, lht, pw_idx),
            "cw_shot": get_ot_rate(shc, sht, cw_idx), "pw_shot": get_ot_rate(shc, sht, pw_idx),
        }
        return pd.DataFrame(data), summary

    return extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41), \
           extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)

# =================================================================
# 3. GIAO DIỆN & RENDER
# =================================================================
def format_vietnam(number):
    if pd.isna(number): return "0"
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or prev == 0:
        val = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{val}</td><td class='col-num'>-</td>"
    
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    
    # Logic màu sắc (inverse=True cho Missort/Backlog: tăng là đỏ, giảm là xanh)
    is_better = diff < 0 if inverse else diff > 0
    bg = "#dcfce7" if is_better else "#fee2e2"
    txt = "#15803d" if is_better else "#b91c1c"
    sign = "+" if diff > 0 else ""
    
    wow_str = f"{sign}{pct:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    
    return f"<td style='background-color: {bg}; color: {txt}; font-weight: bold; text-align: center;'>{wow_str}</td>" \
           f"<td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, summary, primary_color):
    # Tính MTD
    t_vin = df['Inbound Vol'].sum()
    t_vout = df['Outbound Vol'].sum()
    t_tpv = df['Total Process Vol'].sum()
    t_tpw = df['Total Process Wgt'].sum()
    t_ms = df['Missort'].sum()
    t_bl = df['Backlog'].sum()
    
    # Tính MTD OT Rate
    lh_all = df['LH Đúng Giờ'].sum() + df['LH Trễ'].sum()
    sh_all = df['Shuttle Đúng Giờ'].sum() + df['Shuttle Trễ'].sum()
    mtd_lhot = (df['LH Đúng Giờ'].sum() / lh_all * 100) if lh_all > 0 else 0
    mtd_shot = (df['Shuttle Đúng Giờ'].sum() / sh_all * 100) if sh_all > 0 else 0

    # 1. Metrics Cards
    cols = st.columns(6)
    metrics = [("Inbound (MTD)", t_vin), ("Outbound (MTD)", t_vout), ("Xử lý (MTD)", t_tpv), 
               ("Trọng lượng (MTD)", t_tpw), ("Missort (MTD)", t_ms), ("Backlog (MTD)", t_bl)]
    for i, (label, val) in enumerate(metrics):
        cols[i].metric(label, format_vietnam(val))

    # 2. WOW Table
    st.markdown(f"""
    <table class="kpi-table">
        <thead>
            <tr><th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr>
        </thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td><td class="col-metric">LH Đúng Giờ (%)</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{mtd_lhot:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{mtd_shot:.2f}%</td></tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    # 3. Charts
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

    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    with c4:
        fig_lh = go.Figure()
        fig_lh.add_trace(go.Bar(x=df['Ngày'], y=df['LH Đúng Giờ'], name="Đúng", marker_color='#10b981'))
        fig_lh.add_trace(go.Bar(x=df['Ngày'], y=df['LH Trễ'], name="Trễ", marker_color='#f43f5e'))
        fig_lh.update_layout(title="Linehaul (LH)", barmode='stack', plot_bgcolor='white')
        st.plotly_chart(fig_lh, use_container_width=True)
    with c5:
        fig_sh = go.Figure()
        fig_sh.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Đúng Giờ'], name="Đúng", marker_color='#10b981'))
        fig_sh.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Trễ'], name="Trễ", marker_color='#f43f5e'))
        fig_sh.update_layout(title="Shuttle", barmode='stack', plot_bgcolor='white')
        st.plotly_chart(fig_sh, use_container_width=True)
    with c6:
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text=df['Backlog'].apply(format_vietnam))
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        fig_bl.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_bl, use_container_width=True)

# Main
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
t1, t2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

with t1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with t2: render_dashboard(data_bn[0], data_bn[1], "#059669")
