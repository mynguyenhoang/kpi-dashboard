import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# =================================================================
# 1. CẤU HÌNH TRANG & CSS
# =================================================================
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
</style>""", unsafe_allow_html=True)

# =================================================================
# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
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
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not vals: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "=" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else 0.0
            return np.nan
        except: return np.nan

    # Xác định cột bắt đầu (Ngày 1)
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
        
        # Dữ liệu Vận tải
        lh_c = [clean_val(lhc_idx, c) or 0 for c in cols_to_scan]
        lh_t = [clean_val(lht_idx, c) or 0 for c in cols_to_scan]
        sh_c = [clean_val(shc_idx, c) or 0 for c in cols_to_scan]
        sh_t = [clean_val(sht_idx, c) or 0 for c in cols_to_scan]
        
        data["LH Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = [t if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["Shuttle Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = [t if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]

        # WOW Logic (Cột 3,4,5,6 là các tuần)
        valid_weeks = [idx for idx in [3, 4, 5, 6] if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_rate(c_idx, t_idx, col):
            if col == -1: return 0
            c, t = clean_val(c_idx, col), clean_val(t_idx, col)
            return ((c - (t or 0)) / c * 100) if (c and c > 0) else 0

        summary = {
            "cw_vin": clean_val(vin_idx, cw), "pw_vin": clean_val(vin_idx, pw),
            "cw_vout": clean_val(vout_idx, cw), "pw_vout": clean_val(vout_idx, pw),
            "cw_ms": clean_val(ms_idx, cw), "pw_ms": clean_val(ms_idx, pw),
            "cw_bl": clean_val(bl_idx, cw), "pw_bl": clean_val(bl_idx, pw),
            "cw_lhot": get_rate(lhc_idx, lht_idx, cw), "pw_lhot": get_rate(lhc_idx, lht_idx, pw),
            "cw_shot": get_rate(shc_idx, sht_idx, cw), "pw_shot": get_rate(shc_idx, sht_idx, pw)
        }
        return pd.DataFrame(data), summary

    return extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41), \
           extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)

# =================================================================
# 3. GIAO DIỆN HỖ TRỢ
# =================================================================
def format_vietnam(number):
    if pd.isna(number): return "0"
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or prev == 0:
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td>-</td><td class='col-num'>{cur_str}</td><td>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100)
    bg = "#fee2e2" if (diff > 0 if inverse else diff < 0) else "#dcfce7"
    color = "#b91c1c" if (diff > 0 if inverse else diff < 0) else "#15803d"
    sign = "+" if diff > 0 else ""
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{sign}{pct:.1f}%</td>" \
           f"<td class='col-num'>{f'{cur:.2f}%' if is_pct else format_vietnam(cur)}</td>" \
           f"<td class='col-num'>{f'{prev:.2f}%' if is_pct else format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # Tính MTD
    t_vin, t_vout = df['Inbound Vol'].sum(), df['Outbound Vol'].sum()
    t_pvol, t_pwgt = df['Total Process Vol'].sum(), df['Total Process Wgt'].sum()
    t_ms, t_bl = df['Missort'].sum(), df['Backlog'].sum()
    
    lh_ok, lh_tr = df['LH Đúng Giờ'].sum(), df['LH Trễ'].sum()
    sh_ok, sh_tr = df['Shuttle Đúng Giờ'].sum(), df['Shuttle Trễ'].sum()
    lhot_mtd = (lh_ok / (lh_ok + lh_tr) * 100) if (lh_ok + lh_tr) > 0 else 0
    shot_mtd = (sh_ok / (sh_ok + sh_tr) * 100) if (sh_ok + sh_tr) > 0 else 0

    # 1. Metric Cards
    st.markdown("<br>", unsafe_allow_html=True)
    c = st.columns(6)
    metrics = [("Inbound", t_vin), ("Outbound", t_vout), ("Xử lý", t_pvol), ("Trọng lượng", t_pwgt), ("Missort", t_ms), ("Backlog", t_bl)]
    for i, (label, val) in enumerate(metrics):
        c[i].metric(f"{label} (MTD)", format_vietnam(val))

    # 2. WOW Table
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">LH Đúng Giờ (%)</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # 3. Charts - Sản lượng
    st.markdown(f"<h4 style='color:{primary_color}'>1. Biểu Đồ Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig.update_layout(title="Inbound & Outbound", margin=dict(t=40, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig_v = px.bar(df, x='Ngày', y='Total Process Vol', title="Năng suất (Số đơn)", text_auto='.2s')
        fig_v.update_traces(marker_color='#38bdf8', textposition='outside')
        st.plotly_chart(fig_v, use_container_width=True)
    with c3:
        fig_w = px.bar(df, x='Ngày', y='Total Process Wgt', title="Năng suất (Kg)", text_auto='.2s')
        fig_w.update_traces(marker_color='#818cf8', textposition='outside')
        st.plotly_chart(fig_w, use_container_width=True)

    # 4. Charts - Vận tải (Đã hoán đổi vị trí hiển thị)
    st.markdown(f"<h4 style='color:{primary_color}'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    col4, col5, col6 = st.columns([1, 1, 1])
    
    with col4: # Hiển thị Shuttle ở đây
        fig_sh = go.Figure()
        fig_sh.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Đúng Giờ'], name="Đúng", marker_color='#10b981'))
        fig_sh.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Trễ'], name="Trễ", marker_color='#f43f5e'))
        fig_sh.update_layout(title="Vận tải: SHUTTLE", barmode='stack', legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_sh, use_container_width=True)

    with col5: # Hiển thị Linehaul ở đây
        fig_lh = go.Figure()
        fig_lh.add_trace(go.Bar(x=df['Ngày'], y=df['LH Đúng Giờ'], name="Đúng", marker_color='#10b981'))
        fig_lh.add_trace(go.Bar(x=df['Ngày'], y=df['LH Trễ'], name="Trễ", marker_color='#f43f5e'))
        fig_lh.update_layout(title="Vận tải: LINEHAUL", barmode='stack', legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_lh, use_container_width=True)

    with col6:
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Hàng tồn: BACKLOG", text_auto='.2s')
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        st.plotly_chart(fig_bl, use_container_width=True)

# Main App
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
(df_hcm, sum_hcm), (df_bn, sum_bn) = get_data()

t1, t2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with t1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with t2: render_dashboard(df_bn, sum_bn, "#059669")
