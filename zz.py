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
st.markdown("""<style>    .kpi-table {        width: 100%;        border-collapse: collapse;        margin-bottom: 30px;        background-color: white;        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;        box-shadow: 0 1px 3px rgba(0,0,0,0.1);    }    .kpi-table th {        background-color: #1f2937;        color: white;        padding: 10px 12px;        text-align: center;        border: 1px solid #d1d5db;        font-size: 14px;        font-weight: bold;        line-height: 1.4;    }    .kpi-table td {        padding: 10px 12px;        border: 1px solid #d1d5db;        font-size: 14px;        vertical-align: middle;        line-height: 1.4;    }    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }    .col-metric { font-weight: 600; color: #1e293b; }    .col-num { text-align: right; font-family: monospace; font-size: 15px; }    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }    div[data-testid="metric-container"] {        background-color: #ffffff;        border: 1px solid #e2e8f0;        padding: 15px 20px;        border-radius: 8px;        box-shadow: 0 2px 4px rgba(0,0,0,0.02);    }</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": "cli_a9456e412bb89bce", 
            "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except:
        return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token Feishu.")
        return (pd.DataFrame(), {}, {}), (pd.DataFrame(), {}, {})
    
    # Mở rộng dải quét đến cột AS để bốc được cột Monthly Total (cột AM)
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AS80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    res = requests.get(url, headers=headers, timeout=30).json()
    if res.get("code") != 0:
        return (pd.DataFrame(), {}, {}), (pd.DataFrame(), {}, {})
    
    vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55:
        return (pd.DataFrame(), {}, {}), (pd.DataFrame(), {}, {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else 0.0
            return np.nan
        except: return np.nan

    # Xác định cột "1" (Ngày 1)
    start_col_idx = -1
    for c in range(len(vals[3])):
        if str(vals[3][c]).strip() == "1":
            start_col_idx = c
            break
    if start_col_idx == -1: start_col_idx = 6

    # Xác định số ngày hiện tại có dữ liệu để vẽ biểu đồ
    num_days = 1
    for c in range(start_col_idx, len(vals[3])):
        v = str(vals[3][c]).strip()
        if v.isdigit(): num_days = max(num_days, int(v))
        else: break
    
    # CỘT AM (Chỉ số 38 trong mảng 0-index) là Monthly Total trong hình của mày
    MTD_COL = 38 

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
        
        # Lấy trực tiếp số từ cột Monthly Total trên Feishu
        mtd_totals = {
            "vin": clean_val(vin_idx, MTD_COL),
            "vout": clean_val(vout_idx, MTD_COL),
            "win": clean_val(win_idx, MTD_COL),
            "wout": clean_val(wout_idx, MTD_COL),
            "ms": clean_val(ms_idx, MTD_COL),
            "bl": clean_val(bl_idx, MTD_COL),
            "ms_rate": clean_val(ms_rt_idx, MTD_COL)
        }

        # WOW logic giữ nguyên
        valid_weeks = [i for i in [3, 4, 5, 6] if clean_val(vin_idx, i) > 0]
        cw_idx = valid_weeks[-1] if valid_weeks else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_rate(c_idx, t_idx, col):
            if col == -1 or not clean_val(c_idx, col): return 0
            return ((clean_val(c_idx, col) - (clean_val(t_idx, col) or 0)) / clean_val(c_idx, col)) * 100

        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), summary, mtd_totals

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
res_hcm, res_bn = get_data()
df_hcm, sum_hcm, mtd_hcm = res_hcm
df_bn, sum_bn, mtd_bn = res_bn

def format_vietnam(n):
    if pd.isna(n) or n == "": return ""
    return f"{n:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        return f"<td>-</td><td class='col-num'>{cur:.1f}%" if is_pct else f"<td>-</td><td class='col-num'>{format_vietnam(cur)}</td><td>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff/prev*100)
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    sign = "+" if diff > 0 else ""
    return f"<td style='background:#f1f5f9;color:{color};font-weight:bold;text-align:center;'>{sign}{pct:.0f}%</td><td class='col-num'>{cur:.1f}%" if is_pct else f"<td style='background:#f1f5f9;color:{color};font-weight:bold;text-align:center;'>{sign}{pct:.0f}%</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>{format_vietnam(prev)}</td>"

def render_dashboard(df, summary, mtd, primary_color):
    if df.empty: return
    
    # Header Metrics lấy từ mtd (Số Monthly Total từ Feishu)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vietnam(mtd['vin']))
    c2.metric("Tổng Outbound (MTD)", format_vietnam(mtd['vout']))
    c3.metric(f"Tổng Missort (MTD) ({mtd['ms_rate']:.2f}%)", format_vietnam(mtd['ms']))
    c4.metric("Tổng Backlog (MTD)", format_vietnam(mtd['bl']))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    html_table = f"""
    <table class="kpi-table">
        <tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD (Monthly Total)</th></tr>
        <tr><td rowspan="4" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(mtd['vin'])}</td></tr>
        <tr><td class="col-metric">Inbound (kg)</td>{get_wow_cell(summary['cw_win'], summary['pw_win'])}<td class="col-mtd">{format_vietnam(mtd['win'])}</td></tr>
        <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(mtd['vout'])}</td></tr>
        <tr><td class="col-metric">Outbound (kg)</td>{get_wow_cell(summary['cw_wout'], summary['pw_wout'])}<td class="col-mtd">{format_vietnam(mtd['wout'])}</td></tr>
        <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(mtd['ms'])}</td></tr>
        <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(mtd['bl'])}</td></tr>
        <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">Linehaul Đúng Giờ</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">-</td></tr>
        <tr><td class="col-metric">Shuttle Đúng Giờ</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">-</td></tr>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)
    # Phần biểu đồ giữ nguyên
    st.plotly_chart(px.line(df, x='Ngày', y=['Inbound Vol', 'Outbound Vol'], title="Sản lượng hàng ngày"), use_container_width=True)

t1, t2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with t1: render_dashboard(df_hcm, sum_hcm, mtd_hcm, "#0284c7")
with t2: render_dashboard(df_bn, sum_bn, mtd_bn, "#059669")
