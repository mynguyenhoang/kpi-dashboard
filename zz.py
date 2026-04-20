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
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; }
    .kpi-table td { padding: 10px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
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
    except:
        return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
        if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    except:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip()
                if v == "" or "#" in v or "=" in v or v == "None": return np.nan
                return float(v.replace('%', '').replace(',', ''))
            return np.nan
        except: return np.nan

    # Logic tìm ngày và cột
    start_col_idx = 6 # Mặc định cột G
    num_days = 26
    
    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        cols_to_scan = [start_col_idx + i for i in range(num_days)]
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # Xử lý Logic vận tải
        data["LH Đúng Giờ"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Đúng Giờ"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]

        # Weekly Summary (giả định cột 3, 4, 5, 6 là tuần)
        cw_idx = 6 # Current Week
        pw_idx = 5 # Previous Week
        
        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": 95.0, "pw_lhot": 92.0, "cw_shot": 98.0, "pw_shot": 94.0 # Dummy logic for OT
        }
        return pd.DataFrame(data), summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)

data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

def format_vietnam(number):
    if pd.isna(number): return "-"
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    cur = 0 if pd.isna(cur) else cur
    prev = 0 if pd.isna(prev) else prev
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev * 100) if prev != 0 else 0)
    
    color = "#15803d" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#b91c1c"
    arrow = "↑" if diff > 0 else "↓"
    
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    
    return f"""
    <td style='color: {color}; text-align: center; font-weight: bold;'>{arrow} {abs(pct):.0f}%</td>
    <td class='col-num'>{cur_str}</td>
    <td class='col-num'>{prev_str}</td>
    """

def render_tab(df, summary, color):
    if df.empty: 
        st.error("Không có dữ liệu hiển thị.")
        return

    # Metrics
    t_vin = df['Inbound Vol'].sum()
    t_vout = df['Outbound Vol'].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Tổng Outbound (MTD)", format_vietnam(t_vout))
    c3.metric("Tỷ lệ Missort", f"{df['Tỷ lệ Missort (%)'].mean():.2f}%")
    c4.metric("Backlog Hiện Tại", format_vietnam(df['Backlog'].iloc[-1]))

    # Bảng KPI
    html_table = f"""
    <table class="kpi-table">
        <tr>
            <th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th>
        </tr>
        <tr>
            <td rowspan="2" class="col-pillar">Sản Lượng</td>
            <td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td>
        </tr>
        <tr>
            <td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td>
        </tr>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Biểu đồ
    fig = px.line(df, x="Ngày", y=["Inbound Vol", "Outbound Vol"], title="Xu hướng Sản lượng")
    st.plotly_chart(fig, use_container_width=True)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render_tab(df_hcm, sum_hcm, "#0284c7")
with tab2: render_tab(df_bn, sum_bn, "#059669")
