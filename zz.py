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
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px 20px; border-radius: 8px; }
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        return requests.post(url, json=payload, timeout=10).json().get("tenant_access_token")
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

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                s = str(v).replace('%', '').replace(',', '').strip()
                return float(s) if s not in ["", "-", "None"] else np.nan
            return np.nan
        except: return np.nan

    # Mapping cột
    date_row_idx = 3
    start_col_idx = 7 # Cột H (Ngày 1)
    monthly_total_col_idx = 37 # Cột AL (Monthly Total)
    weekly_col_idxs = [3, 4, 5, 6] # D, E, F, G
    
    cols_to_scan = [start_col_idx + i for i in range(31) if (start_col_idx + i) < monthly_total_col_idx]

    def extract_hub_data(vin, vout, win, wout, ms, ms_rt, bl, shc, lhc, sht, lht):
        # Lấy dữ liệu biểu đồ hàng ngày
        data = {"Ngày": [f"Ngày {i+1}" for i in range(len(cols_to_scan))]}
        data["Inbound Vol"] = [clean_val(vin, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl, c) for c in cols_to_scan]
        data["LH Đúng Giờ"] = [clean_val(lhc, c) - clean_val(lht, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht, c) for c in cols_to_scan]
        data["Shuttle Đúng Giờ"] = [clean_val(shc, c) - clean_val(sht, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht, c) for c in cols_to_scan]

        # Lấy Weekly & MTD
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin, idx))]
        cw = valid_weeks[-1] if valid_weeks else -1
        pw = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_rate(c_idx, t_idx, col):
            total = clean_val(c_idx, col)
            late = clean_val(t_idx, col)
            return ((total - late) / total * 100) if (total and total > 0) else 0

        summary = {
            "cw_vin": clean_val(vin, cw), "pw_vin": clean_val(vin, pw),
            "cw_vout": clean_val(vout, cw), "pw_vout": clean_val(vout, pw),
            "cw_win": clean_val(win, cw), "pw_win": clean_val(win, pw),
            "cw_wout": clean_val(wout, cw), "pw_wout": clean_val(wout, pw),
            "cw_ms": clean_val(ms, cw), "pw_ms": clean_val(ms, pw),
            "cw_bl": clean_val(bl, cw), "pw_bl": clean_val(bl, pw),
            "cw_lhot": get_rate(lhc, lht, cw), "pw_lhot": get_rate(lhc, lht, pw),
            "cw_shot": get_rate(shc, sht, cw), "pw_shot": get_rate(shc, sht, pw),
            # TRỰC TIẾP TỪ CỘT MONTHLY TOTAL
            "mtd_vin": clean_val(vin, monthly_total_col_idx),
            "mtd_vout": clean_val(vout, monthly_total_col_idx),
            "mtd_win": clean_val(win, monthly_total_col_idx),
            "mtd_wout": clean_val(wout, monthly_total_col_idx),
            "mtd_ms": clean_val(ms, monthly_total_col_idx),
            "mtd_ms_rt": clean_val(ms_rt, monthly_total_col_idx),
            "mtd_bl": clean_val(bl, monthly_total_col_idx),
            "mtd_lhot": get_rate(lhc, lht, monthly_total_col_idx),
            "mtd_shot": get_rate(shc, sht, monthly_total_col_idx)
        }
        return pd.DataFrame(data), summary

    # MAP THEO INDEX BẠN CUNG CẤP
    # Params: vin, vout, win, wout, ms, ms_rt, bl, sh_total, lh_total, sh_late, lh_late
    df_hcm, sum_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 39, 40, 41)
    df_bn, sum_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 48, 49, 50)
    
    return (df_hcm, sum_hcm), (df_bn, sum_bn)

# 3. HIỂN THỊ
st.markdown("<h2 style='text-align: center; font-weight: 800;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
(df_hcm, sum_hcm), (df_bn, sum_bn) = get_data()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vn(n):
    return f"{n:,.0f}".replace(",", ".") if pd.notna(n) else ""

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(prev) or prev == 0: return f"<td style='text-align:center;'>-</td><td class='col-num'>{cur:.2f}%" if is_pct else f"<td style='text-align:center;'>-</td><td class='col-num'>{format_vn(cur)}</td><td class='col-num'>-</td>"
    diff = (cur - prev) if is_pct else ((cur - prev) / prev * 100)
    color = "#15803d" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#b91c1c"
    bg = "#dcfce7" if color == "#15803d" else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background:{bg};color:{color};font-weight:bold;text-align:center;'>{sign}{diff:.0f}%</td><td class='col-num'>{cur:.2f}%" if is_pct else f"<td style='background:{bg};color:{color};font-weight:bold;text-align:center;'>{sign}{diff:.0f}%</td><td class='col-num'>{format_vn(cur)}</td><td class='col-num'>{format_vn(prev)}</td>"

def render(df, s, color):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vn(s['mtd_vin']))
    c2.metric("Tổng Outbound (MTD)", format_vn(s['mtd_vout']))
    c3.metric(f"Missort MTD ({s['mtd_ms_rt']:.2f}%)", format_vn(s['mtd_ms']))
    c4.metric("Backlog Hiện Tại", format_vn(s['mtd_bl']))

    html = f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="4" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(s['cw_vin'], s['pw_vin'])}<td class="col-mtd">{format_vn(s['mtd_vin'])}</td></tr>
            <tr><td class="col-metric">Inbound (kg)</td>{get_wow_cell(s['cw_win'], s['pw_win'])}<td class="col-mtd">{format_vn(s['mtd_win'])}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(s['cw_vout'], s['pw_vout'])}<td class="col-mtd">{format_vn(s['mtd_vout'])}</td></tr>
            <tr><td class="col-metric">Outbound (kg)</td>{get_wow_cell(s['cw_wout'], s['pw_wout'])}<td class="col-mtd">{format_vn(s['mtd_wout'])}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(s['cw_ms'], s['pw_ms'], inverse=True)}<td class="col-mtd">{format_vn(s['mtd_ms'])}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(s['cw_bl'], s['pw_bl'], inverse=True)}<td class="col-mtd">{format_vn(s['mtd_bl'])}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">Linehaul Đúng Giờ</td>{get_wow_cell(s['cw_lhot'], s['pw_lhot'], is_pct=True)}<td class="col-mtd">{s['mtd_lhot']:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ</td>{get_wow_cell(s['cw_shot'], s['pw_shot'], is_pct=True)}<td class="col-mtd">{s['mtd_shot']:.2f}%</td></tr>
        </tbody></table>"""
    st.markdown(html, unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        f1 = go.Figure()
        f1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy'))
        f1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(dash='dot')))
        f1.update_layout(title="Sản lượng hàng ngày", plot_bgcolor='white', height=300)
        st.plotly_chart(f1, use_container_width=True)
    with col_b:
        f2 = px.bar(df, x="Ngày", y="Backlog", title="Backlog hàng ngày", color_discrete_sequence=['#f59e0b'])
        f2.update_layout(plot_bgcolor='white', height=300)
        st.plotly_chart(f2, use_container_width=True)

with tab1: render(df_hcm, sum_hcm, "#0284c7")
with tab2: render(df_bn, sum_bn, "#059669")
