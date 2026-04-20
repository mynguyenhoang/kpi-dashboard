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
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; line-height: 1.4; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; line-height: 1.4; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
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
    if not token:
        st.error("Không lấy được Token Feishu.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    res_data = requests.get(url, headers=headers, timeout=30).json()
    if res_data.get("code") != 0: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    
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

    # Vị trí các cột dữ liệu theo bảng Feishu
    weekly_col_idxs = [3, 4, 5, 6] # Các cột W15-W18 (D, E, F, G)
    start_day_col = 7 # Cột H bắt đầu Ngày 1
    num_days = 30
    cols_days = [start_day_col + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        # Dữ liệu theo ngày (Chỉ lấy từ cột Ngày 1 trở đi)
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_days]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_days]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_days]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_days]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_days]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_days] 
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_days]
        
        # Logistic vận tải (Dùng list comprehension để xử lý NaN)
        lh_c = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_days]
        lh_t = [clean_val(lht_idx, c) if pd.notna(clean_val(lht_idx, c)) else 0 for c in cols_days]
        sh_c = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_days]
        sh_t = [clean_val(sht_idx, c) if pd.notna(clean_val(sht_idx, c)) else 0 for c in cols_days]

        data["LH Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = [t if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        data["Shuttle Đúng Giờ"] = [(c - t) if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = [t if c > 0 else np.nan for c, t in zip(sh_c, sh_t)]

        # Lấy dữ liệu WOW (So sánh tuần gần nhất có dữ liệu)
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
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
        }
        return pd.DataFrame(data), summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. HIỂN THỊ
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inverse else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background-color: {bg}; color: {color}; font-weight: bold; text-align: center;'>{sign}{pct:.0f}%</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>{format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    # TÍNH MTD CHUẨN: Chỉ tính trên các cột Ngày thực tế
    t_vin = df['Inbound Vol'].sum(skipna=True)
    t_vout = df['Outbound Vol'].sum(skipna=True)
    t_win = df['Inbound Wgt'].sum(skipna=True)
    t_wout = df['Outbound Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    
    lh_total = df['LH Đúng Giờ'].sum() + df['LH Trễ'].sum()
    sh_total = df['Shuttle Đúng Giờ'].sum() + df['Shuttle Trễ'].sum()
    lhot_mtd = (df['LH Đúng Giờ'].sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df['Shuttle Đúng Giờ'].sum() / sh_total * 100) if sh_total > 0 else 0
    ms_rate_mtd = (t_ms / (t_vin + t_vout) * 100) if (t_vin + t_vout) > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Tổng Outbound (MTD)", format_vietnam(t_vout))
    c3.metric(f"Missort ({ms_rate_mtd:.2f}%)", format_vietnam(t_ms))
    c4.metric("Backlog (MTD)", format_vietnam(t_bl))

    html = f"""
    <table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD (Tổng Ngày)</th></tr></thead>
        <tbody>
            <tr><td rowspan="4" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Inbound (kg)</td>{get_wow_cell(summary['cw_win'], summary['pw_win'])}<td class="col-mtd">{format_vietnam(t_win)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td class="col-metric">Outbound (kg)</td>{get_wow_cell(summary['cw_wout'], summary['pw_wout'])}<td class="col-mtd">{format_vietnam(t_wout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">Linehaul (%)</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle (%)</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td></tr>
        </tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)

    # 3. BẢNG DỮ LIỆU THÔ (Ẩn số 0)
    df_show = df.copy()
    for col in df_show.columns:
        if col != "Ngày":
            if "Tỷ lệ" in col: df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
            else: df_show[col] = df_show[col].apply(format_vietnam)
    with st.expander("Bảng chi tiết"):
        st.dataframe(df_show.set_index("Ngày").T, use_container_width=True)

with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
