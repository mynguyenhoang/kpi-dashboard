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
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU (Logic giữ nguyên)
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
        
        data["LH Tổng"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Tổng"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        data["LH Đúng Giờ"] = [(c - t) if (pd.notna(c) and pd.notna(t)) else np.nan for c, t in zip(data["LH Tổng"], data["LH Trễ"])]
        data["Shuttle Đúng Giờ"] = [(c - t) if (pd.notna(c) and pd.notna(t)) else np.nan for c, t in zip(data["Shuttle Tổng"], data["Shuttle Trễ"])]

        valid_weeks = [3, 4, 5, 6]
        cw_idx = -1
        for idx in valid_weeks:
            if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0: cw_idx = idx
        pw_idx = valid_weeks[valid_weeks.index(cw_idx)-1] if cw_idx in valid_weeks and valid_weeks.index(cw_idx) > 0 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
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
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu...")
    st.stop()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vn(n):
    return f"{n:,.0f}".replace(",", ".") if pd.notna(n) else ""

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur:.2f}%" if is_pct else f"-</td><td class='col-num'>{format_vn(cur)}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    bg, txt = ("#dcfce7", "#15803d") if (diff > 0 if not inverse else diff < 0) else ("#fee2e2", "#b91c1c")
    if diff == 0: bg, txt = "transparent", "#333"
    return f"<td style='background-color: {bg}; color: {txt}; font-weight: bold; text-align: center;'>{'+' if diff > 0 else ''}{pct:.0f}%</td><td class='col-num'>{'%.2f' % cur + '%' if is_pct else format_vn(cur)}</td><td class='col-num'>{'%.2f' % prev + '%' if is_pct else format_vn(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    # Metrics MTD
    c = st.columns(6)
    m_list = [("Inbound", df['Inbound Vol'].sum()), ("Outbound", df['Outbound Vol'].sum()), ("Xử lý", df['Total Process Vol'].sum()), ("Trọng lượng", df['Total Process Wgt'].sum()), ("Missort", df['Missort'].sum()), ("Backlog", df['Backlog'].sum())]
    for col, (l, v) in zip(c, m_list): col.metric(f"{l} (MTD)", format_vn(v))

    # WOW Table
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vn(df['Inbound Vol'].sum())}</td></tr>
            <tr><td class="col-metric">Outbound</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vn(df['Outbound Vol'].sum())}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td><td class="col-metric">Missort</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vn(df['Missort'].sum())}</td></tr>
            <tr><td class="col-metric">Backlog</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vn(df['Backlog'].sum())}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td><td class="col-metric">LH Đúng Giờ</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{(df['LH Đúng Giờ'].sum()/df['LH Tổng'].sum()*100):.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{(df['Shuttle Đúng Giờ'].sum()/df['Shuttle Tổng'].sum()*100):.2f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # 4. QUẢN LÝ VẬN TẢI (Tách riêng Tổng và Trễ)
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải (Linehaul & Shuttle)</h4>", unsafe_allow_html=True)
    
    # Row 1: Linehaul
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.plotly_chart(px.bar(df, x='Ngày', y='LH Tổng', title="Linehaul - Tổng số chuyến", text_auto=True).update_traces(marker_color='#10b981').update_layout(plot_bgcolor='white', height=300), use_container_width=True)
    with r1c2:
        st.plotly_chart(px.bar(df, x='Ngày', y='LH Trễ', title="Linehaul - Tổng số chuyến TRỄ", text_auto=True).update_traces(marker_color='#ef4444').update_layout(plot_bgcolor='white', height=300), use_container_width=True)

    # Row 2: Shuttle
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.plotly_chart(px.bar(df, x='Ngày', y='Shuttle Tổng', title="Shuttle - Tổng số chuyến", text_auto=True).update_traces(marker_color='#3b82f6').update_layout(plot_bgcolor='white', height=300), use_container_width=True)
    with r2c2:
        st.plotly_chart(px.bar(df, x='Ngày', y='Shuttle Trễ', title="Shuttle - Tổng số chuyến TRỄ", text_auto=True).update_traces(marker_color='#f43f5e').update_layout(plot_bgcolor='white', height=300), use_container_width=True)

    # 5. HÀNG TỒN BACKLOG
    st.markdown(f"<h4 style='color: {primary_color};'>3. Hàng tồn Backlog</h4>", unsafe_allow_html=True)
    st.plotly_chart(px.bar(df, x="Ngày", y="Backlog", text_auto=True).update_traces(marker_color='#f59e0b').update_layout(plot_bgcolor='white', height=350), use_container_width=True)

    with st.expander("🔍 Chi tiết dữ liệu thô"): st.dataframe(df.set_index("Ngày").T, use_container_width=True)

with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
