import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS (Giữ nguyên)
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
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
        return requests.post(url, json=payload, timeout=10).json().get("tenant_access_token")
    except: return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers, timeout=30).json()
    vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                s = str(v).replace('%', '').replace(',', '').strip()
                return float(s) if s not in ["", "-", "None"] else np.nan
            return np.nan
        except: return np.nan

    # Cấu hình cột
    start_col_idx = 7 # Cột H (Ngày 1)
    monthly_total_col_idx = 37 # Cột AL (Monthly Total trên Feishu)
    weekly_col_idxs = [3, 4, 5, 6]
    cols_to_scan = [start_col_idx + i for i in range(31) if (start_col_idx + i) < monthly_total_col_idx]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(len(cols_to_scan))]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # Vận tải
        lh_c = [clean_val(lhc_idx, c) or 0 for c in cols_to_scan]
        lh_t = [clean_val(lht_idx, c) or 0 for c in cols_to_scan]
        sh_c = [clean_val(shc_idx, c) or 0 for c in cols_to_scan]
        sh_t = [clean_val(sht_idx, c) or 0 for c in cols_to_scan]
        data["LH Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = [t if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["Shuttle Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = [t if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]

        # Lấy WOW
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx))]
        cw_idx = valid_weeks[-1] if valid_weeks else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col):
            chuyen = clean_val(c_idx, col)
            tre = clean_val(t_idx, col)
            return ((chuyen - tre) / chuyen * 100) if (chuyen and chuyen > 0) else 0

        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
            # FIX MTD: Lấy trực tiếp từ cột AL (Monthly Total)
            "mtd_vin": clean_val(vin_idx, monthly_total_col_idx),
            "mtd_vout": clean_val(vout_idx, monthly_total_col_idx),
            "mtd_win": clean_val(win_idx, monthly_total_col_idx),
            "mtd_wout": clean_val(wout_idx, monthly_total_col_idx),
            "mtd_ms": clean_val(ms_idx, monthly_total_col_idx),
            "mtd_ms_rt": clean_val(ms_rt_idx, monthly_total_col_idx),
            "mtd_bl": clean_val(bl_idx, monthly_total_col_idx),
            "mtd_lhot": get_ot_rate(lhc_idx, lht_idx, monthly_total_col_idx),
            "mtd_shot": get_ot_rate(shc_idx, sht_idx, monthly_total_col_idx)
        }
        return pd.DataFrame(data), summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 39, 40, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 48, 49, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN (Giữ nguyên)
st.markdown("<h2 style='text-align: center; font-weight: 800;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    color = "#15803d" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#b91c1c"
    bg = "#dcfce7" if color == "#15803d" else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background:{bg};color:{color};font-weight:bold;text-align:center;'>{sign}{diff:.0f}%</td><td class='col-num'>{cur:.2f}%" if is_pct else f"<td style='background:{bg};color:{color};font-weight:bold;text-align:center;'>{sign}{diff:.0f}%</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>{format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    s = summary
    
    # Header Metrics lấy từ MTD chuẩn
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vietnam(s['mtd_vin']))
    c2.metric("Tổng Outbound (MTD)", format_vietnam(s['mtd_vout']))
    c3.metric(f"Missort MTD ({s['mtd_ms_rt']:.2f}%)", format_vietnam(s['mtd_ms']))
    c4.metric("Backlog Tồn Đọng", format_vietnam(s['mtd_bl']))

    # Bảng Mapping trực tiếp giá trị MTD
    html_table = f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="4" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(s['cw_vin'], s['pw_vin'])}<td class="col-mtd">{format_vietnam(s['mtd_vin'])}</td></tr>
            <tr><td class="col-metric">Inbound (kg)</td>{get_wow_cell(s['cw_win'], s['pw_win'])}<td class="col-mtd">{format_vietnam(s['mtd_win'])}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(s['cw_vout'], s['pw_vout'])}<td class="col-mtd">{format_vietnam(s['mtd_vout'])}</td></tr>
            <tr><td class="col-metric">Outbound (kg)</td>{get_wow_cell(s['cw_wout'], s['pw_wout'])}<td class="col-mtd">{format_vietnam(s['mtd_wout'])}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(s['cw_ms'], s['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(s['mtd_ms'])}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(s['cw_bl'], s['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(s['mtd_bl'])}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">Linehaul Đúng Giờ</td>{get_wow_cell(s['cw_lhot'], s['pw_lhot'], is_pct=True)}<td class="col-mtd">{s['mtd_lhot']:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ</td>{get_wow_cell(s['cw_shot'], s['pw_shot'], is_pct=True)}<td class="col-mtd">{s['mtd_shot']:.2f}%</td></tr>
        </tbody></table>"""
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Biểu đồ (Giữ nguyên)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        f1 = go.Figure()
        f1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy'))
        f1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(dash='dot')))
        f1.update_layout(title="Sản lượng hàng ngày", height=350, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(f1, use_container_width=True)
    with col_chart2:
        f2 = px.bar(df, x="Ngày", y="Backlog", title="Backlog cuối ngày")
        f2.update_layout(height=350, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(f2, use_container_width=True)

with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
