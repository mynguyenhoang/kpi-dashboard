import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: sans-serif; }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px; text-align: center; border: 1px solid #d1d5db; }
    .kpi-table td { padding: 10px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; color: #15803d; }
</style>
""", unsafe_allow_html=True)

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

    if not vals: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip()
                if v == "" or "#" in v or "=" in v: return np.nan
                return float(v.replace('%', '').replace(',', ''))
            return np.nan
        except: return np.nan

    # 1. TÌM CỘT MTD (CỘT CUỐI CÙNG CỦA DẢI DỮ LIỆU)
    # Giả sử cột MTD là cột cuối cùng bên phải (thường là cột AQ hoặc tương tự)
    mtd_col_idx = len(vals[4]) - 1 

    # 2. TÌM CÁC CỘT NGÀY ĐỂ VẼ BIỂU ĐỒ
    start_col_idx = 6
    for c in range(2, len(vals[3])):
        if str(vals[3][c]).strip() == "1":
            start_col_idx = c
            break
    
    num_days = 0
    for c in range(start_col_idx, mtd_col_idx): # Chỉ quét đến trước cột MTD
        if str(vals[3][c]).strip().isdigit(): num_days += 1
        else: break
    
    cols_day = [start_col_idx + i for i in range(num_days)]
    weekly_cols = [3, 4, 5, 6] # W1, W2, W3, W4

    def extract_hub_data(vin, vout, win, wout, ms, ms_rt, bl, sh_c, sh_t, lh_c, lh_t):
        # Data biểu đồ (Daily)
        df_daily = pd.DataFrame({
            "Ngày": [f"Ngày {i+1}" for i in range(num_days)],
            "Inbound Vol": [clean_val(vin, c) for c in cols_day],
            "Outbound Vol": [clean_val(vout, c) for c in cols_day],
            "Missort": [clean_val(ms, c) for c in cols_day],
            "Tỷ lệ Missort (%)": [clean_val(ms_rt, c) for c in cols_day],
            "Backlog": [clean_val(bl, c) for c in cols_day],
            "LH Đúng Giờ": [(clean_val(lh_c, c) or 0) - (clean_val(lh_t, c) or 0) for c in cols_day],
            "LH Trễ": [clean_val(lh_t, c) for c in cols_day],
            "Shuttle Đúng Giờ": [(clean_val(sh_c, c) or 0) - (clean_val(sh_t, c) or 0) for c in cols_day],
            "Shuttle Trễ": [clean_val(sh_t, c) for c in cols_day]
        })

        # Summary lấy TRỰC TIẾP từ cột MTD và các cột Tuần
        valid_weeks = [idx for idx in weekly_cols if pd.notna(clean_val(vin, idx)) and clean_val(vin, idx) > 0]
        cw = valid_weeks[-1] if valid_weeks else -1
        pw = valid_weeks[-2] if len(valid_weeks) > 1 else -1

        summary = {
            # Tuần
            "cw_vin": clean_val(vin, cw), "pw_vin": clean_val(vin, pw),
            "cw_vout": clean_val(vout, cw), "pw_vout": clean_val(vout, pw),
            "cw_win": clean_val(win, cw), "pw_win": clean_val(win, pw),
            "cw_wout": clean_val(wout, cw), "pw_wout": clean_val(wout, pw),
            "cw_ms": clean_val(ms, cw), "pw_ms": clean_val(ms, pw),
            "cw_bl": clean_val(bl, cw), "pw_bl": clean_val(bl, pw),
            "cw_lhot": (((clean_val(lh_c, cw) or 0)-(clean_val(lh_t, cw) or 0))/(clean_val(lh_c, cw) or 1)*100),
            "cw_shot": (((clean_val(sh_c, cw) or 0)-(clean_val(sh_t, cw) or 0))/(clean_val(sh_c, cw) or 1)*100),
            # MTD - LẤY TRỰC TIẾP TỪ CỘT MTD, KHÔNG SUM
            "mtd_vin": clean_val(vin, mtd_col_idx),
            "mtd_vout": clean_val(vout, mtd_col_idx),
            "mtd_win": clean_val(win, mtd_col_idx),
            "mtd_wout": clean_val(wout, mtd_col_idx),
            "mtd_ms": clean_val(ms, mtd_col_idx),
            "mtd_bl": clean_val(bl, mtd_col_idx),
            "mtd_lhot": clean_val(42 if vin==4 else 51, mtd_col_idx), # Lấy % từ dòng tỷ lệ có sẵn
            "mtd_shot": clean_val(43 if vin==4 else 52, mtd_col_idx)
        }
        return df_daily, summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# --- PHẦN HIỂN THỊ ---
st.markdown("<h2 style='text-align: center;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()

def format_num(n):
    if pd.isna(n) or n == "": return "-"
    return f"{n:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(prev) or prev == 0: return f"<td>-</td><td class='col-num'>{cur}</td><td>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff/prev*100)
    color = "#15803d" if (diff < 0 if inverse else diff > 0) else "#b91c1c"
    return f"<td style='color:{color}; font-weight:bold; text-align:center;'>{'+' if diff>0 else ''}{pct:.1f}%</td><td class='col-num'>{format_num(cur)}</td><td class='col-num'>{format_num(prev)}</td>"

def render(df, s):
    # Header Metrics lấy từ mtd_...
    c = st.columns(4)
    c[0].metric("Inbound MTD", format_num(s['mtd_vin']))
    c[1].metric("Outbound MTD", format_num(s['mtd_vout']))
    c[2].metric("Missort MTD", format_num(s['mtd_ms']))
    c[3].metric("Backlog MTD", format_num(s['mtd_bl']))

    html = f"""
    <table class="kpi-table">
        <tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD (Từ Sheet)</th></tr>
        <tr><td rowspan="2" class="col-pillar">Sản Lượng</td><td>Inbound (đơn)</td>{get_wow_cell(s['cw_vin'], s['pw_vin'])}<td class="col-mtd">{format_num(s['mtd_vin'])}</td></tr>
        <tr><td>Outbound (đơn)</td>{get_wow_cell(s['cw_vout'], s['pw_vout'])}<td class="col-mtd">{format_num(s['mtd_vout'])}</td></tr>
        <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td>Missort (đơn)</td>{get_wow_cell(s['cw_ms'], s['pw_ms'], inverse=True)}<td class="col-mtd">{format_num(s['mtd_ms'])}</td></tr>
        <tr><td>Backlog (đơn)</td>{get_wow_cell(s['cw_bl'], s['pw_bl'], inverse=True)}<td class="col-mtd">{format_num(s['mtd_bl'])}</td></tr>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.plotly_chart(px.line(df, x="Ngày", y=["Inbound Vol", "Outbound Vol"], title="Xu hướng ngày"), use_container_width=True)

t1, t2 = st.tabs(["HCM", "BẮC NINH"])
with t1: render(data_hcm[0], data_hcm[1])
with t2: render(data_bn[0], data_bn[1])
