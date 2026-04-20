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
st.markdown("""
<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
</style>
""", unsafe_allow_html=True)

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
        if res.get("code") != 0: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not vals or len(vals) < 51: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip()
                if v == "" or "#" in v or "=" in v: return np.nan
                return float(v.replace('%', '').replace(',', ''))
            return np.nan
        except: return np.nan

    # Tìm cột bắt đầu (Ngày 1)
    start_col_idx = 6
    for c in range(2, len(vals[3])):
        if str(vals[3][c]).strip() == "1":
            start_col_idx = c
            break
    
    # Xác định số ngày đã có dữ liệu
    num_days = 0
    for c in range(start_col_idx, len(vals[3])):
        if str(vals[3][c]).strip().isdigit(): num_days += 1
        else: break
    
    cols_to_scan = [start_col_idx + i for i in range(num_days)]
    weekly_col_idxs = [3, 4, 5, 6] # Cột tuần W1, W2, W3, W4

    def extract_hub_data(vin, vout, win, wout, ms, ms_rt, bl, sh_c, sh_t, lh_c, lh_t):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl, c) for c in cols_to_scan]
        
        # Xử lý Vận tải
        data["LH Đúng Giờ"] = [(clean_val(lh_c, c) or 0) - (clean_val(lh_t, c) or 0) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lh_t, c) for c in cols_to_scan]
        data["Shuttle Đúng Giờ"] = [(clean_val(sh_c, c) or 0) - (clean_val(sh_t, c) or 0) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sh_t, c) for c in cols_to_scan]

        # Weekly Summary
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin, idx)) and clean_val(vin, idx) > 0]
        cw = valid_weeks[-1] if valid_weeks else -1
        pw = valid_weeks[-2] if len(valid_weeks) > 1 else -1

        def calc_ot(c_idx, t_idx, col):
            total = clean_val(c_idx, col)
            late = clean_val(t_idx, col) or 0
            return ((total - late) / total * 100) if total and total > 0 else 0

        summary = {
            "cw_vin": clean_val(vin, cw), "pw_vin": clean_val(vin, pw),
            "cw_vout": clean_val(vout, cw), "pw_vout": clean_val(vout, pw),
            "cw_win": clean_val(win, cw), "pw_win": clean_val(win, pw),
            "cw_wout": clean_val(wout, cw), "pw_wout": clean_val(wout, pw),
            "cw_ms": clean_val(ms, cw), "pw_ms": clean_val(ms, pw),
            "cw_bl": clean_val(bl, cw), "pw_bl": clean_val(bl, pw),
            "cw_lhot": calc_ot(lh_c, lh_t, cw), "pw_lhot": calc_ot(lh_c, lh_t, pw),
            "cw_shot": calc_ot(sh_c, sh_t, cw), "pw_shot": calc_ot(sh_c, sh_t, pw),
        }
        return pd.DataFrame(data), summary

    # Gọi hàm trích xuất với Index chuẩn của bạn
    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu từ Feishu...")
    st.stop()

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(prev) or prev == 0:
        val = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{val}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    
    is_good = (diff < 0 if inverse else diff > 0)
    bg = "#dcfce7" if is_good else "#fee2e2"
    txt = "#15803d" if is_good else "#b91c1c"
    if diff == 0: bg, txt = "transparent", "#333"

    sign = "+" if diff > 0 else ""
    wow_str = f"{sign}{pct:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    
    return f"<td style='background-color: {bg}; color: {txt}; font-weight: bold; text-align: center;'>{wow_str}</td><td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, summary, primary_color):
    t_vin = df['Inbound Vol'].sum(skipna=True)
    t_vout = df['Outbound Vol'].sum(skipna=True)
    t_win = df['Inbound Wgt'].sum(skipna=True)
    t_wout = df['Outbound Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    
    # Header Metrics
    cols = st.columns(4)
    cols[0].metric("Tổng Inbound (MTD)", format_vietnam(t_vin))
    cols[1].metric("Tổng Outbound (MTD)", format_vietnam(t_vout))
    cols[2].metric("Tổng Missort (MTD)", format_vietnam(t_ms))
    cols[3].metric("Backlog Cuối", format_vietnam(df['Backlog'].iloc[-1] if not df.empty else 0))

    # Bảng KPI
    html = f"""
    <table class="kpi-table">
        <thead>
            <tr><th>KPI</th><th>Hạng mục</th><th style="width:100px">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr>
        </thead>
        <tbody>
            <tr><td rowspan="4" class="col-pillar" style="color:#0ea5e9">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Inbound (kg)</td>{get_wow_cell(summary['cw_win'], summary['pw_win'])}<td class="col-mtd">{format_vietnam(t_win)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td class="col-metric">Outbound (kg)</td>{get_wow_cell(summary['cw_wout'], summary['pw_wout'])}<td class="col-mtd">{format_vietnam(t_wout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981">Vận Tải</td><td class="col-metric">Linehaul Đúng Giờ</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{(df['LH Đúng Giờ'].sum()/ (df['LH Đúng Giờ'].sum()+df['LH Trễ'].sum())*100 if (df['LH Đúng Giờ'].sum()+df['LH Trễ'].sum()) > 0 else 0):.1f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{(df['Shuttle Đúng Giờ'].sum()/ (df['Shuttle Đúng Giờ'].sum()+df['Shuttle Trễ'].sum())*100 if (df['Shuttle Đúng Giờ'].sum()+df['Shuttle Trễ'].sum()) > 0 else 0):.1f}%</td></tr>
        </tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Biểu đồ
    c1, c2 = st.columns(2)
    with c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig1.update_layout(title="Sản lượng hàng ngày", plot_bgcolor='white', height=350)
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Missort", marker_color='#cbd5e1'), secondary_y=False)
        fig2.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", line=dict(color='#ef4444')), secondary_y=True)
        fig2.update_layout(title="Phân tích Missort", plot_bgcolor='white', height=350)
        st.plotly_chart(fig2, use_container_width=True)

    # Bảng thô
    with st.expander("🔍 Xem Bảng Dữ Liệu Chi Tiết"):
        st.dataframe(df.set_index("Ngày").T, use_container_width=True)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
