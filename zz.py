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

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU (Giữ nguyên 100% logic gốc)
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
    
    res_data = None
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            time.sleep(2)
        except: continue
    
    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "=" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except: return np.nan

    weekly_col_idxs = [3, 4, 5, 6] 
    date_row_idx = 3 
    start_col_idx = -1
    for c in range(2, len(vals[date_row_idx])):
        if str(vals[date_row_idx][c]).strip() == "1":
            start_col_idx = c
            break
    num_days = 26 if start_col_idx == -1 else 30 # Tùy chỉnh theo thực tế
    start_col_idx = start_col_idx if start_col_idx != -1 else 6
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
        
        lh_c_list = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_to_scan]
        lh_t_list = [clean_val(lht_idx, c) if pd.notna(clean_val(lht_idx, c)) else 0 for c in cols_to_scan]
        sh_c_list = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_to_scan]
        sh_t_list = [clean_val(sht_idx, c) if pd.notna(clean_val(sht_idx, c)) else 0 for c in cols_to_scan]

        data["LH Tổng"] = [c if c > 0 else np.nan for c in lh_c_list]
        data["LH Trễ"] = [t if t > 0 else np.nan for t in lh_t_list]
        data["SH Tổng"] = [c if c > 0 else np.nan for c in sh_c_list]
        data["SH Trễ"] = [t if t > 0 else np.nan for t in sh_t_list]
        data["LH Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(lh_c_list, lh_t_list)]
        data["Shuttle Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(sh_c_list, sh_t_list)]

        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

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

# 3. GIAO DIỆN (Giữ logic cũ, sửa UI vận tải)
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

def format_vietnam(number):
    if pd.isna(number): return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or prev == 0: return f"<td>-</td><td class='col-num'>-</td><td>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100)
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inverse else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold;'>{sign}{pct:.0f}%</td><td class='col-num'>{cur:.1f}%" if is_pct else f"<td style='background-color:{bg}; color:{color}; font-weight:bold;'>{sign}{pct:.0f}%</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>{format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    # 1. METRICS (Giữ nguyên logic tính MTD của bạn)
    t_vin = df['Inbound Vol'].sum()
    t_vout = df['Outbound Vol'].sum()
    t_bl = df['Backlog'].last_valid_index() # Hoặc sum tùy logic cũ
    
    # 2. WOW TABLE (Giữ nguyên logic của bạn)
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # 4. BIỂU ĐỒ VẬN TẢI & HÀNG TỒN (SỬA THEO HÌNH NHƯNG GIỮ DATA CŨ)
    st.markdown(f"#### 2. Quản lý Vận Tải & Hàng Tồn")
    
    # Biểu đồ to (LH vs Shuttle)
    fig_total = go.Figure()
    fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['LH Tổng'], name='Linehaul', marker_color='#3498db', text=df['LH Tổng'], textposition='outside'))
    fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['SH Tổng'], name='Shuttle', marker_color='#2ecc71', text=df['SH Tổng'], textposition='outside'))
    fig_total.update_layout(barmode='group', plot_bgcolor='white', height=350, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_total, use_container_width=True)

    # 3 Biểu đồ nhỏ hàng dưới
    c1, c2, c3 = st.columns(3)
    with c1:
        f1 = px.bar(df, x='Ngày', y='LH Trễ', title="Tổng chuyến Linehaul TRỄ", text='LH Trễ')
        f1.update_traces(marker_color='#ef4444', textposition='outside').update_layout(plot_bgcolor='white', height=280)
        st.plotly_chart(f1, use_container_width=True)
    with c2:
        f2 = px.bar(df, x='Ngày', y='SH Trễ', title="Tổng chuyến Shuttle TRỄ", text='SH Trễ')
        f2.update_traces(marker_color='#ef4444', textposition='outside').update_layout(plot_bgcolor='white', height=280)
        st.plotly_chart(f2, use_container_width=True)
    with c3:
        f3 = px.bar(df, x='Ngày', y='Backlog', title="Backlog tồn đọng", text=df['Backlog'].apply(format_vietnam))
        f3.update_traces(marker_color='#f59e0b', textposition='outside').update_layout(plot_bgcolor='white', height=280)
        st.plotly_chart(f3, use_container_width=True)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
