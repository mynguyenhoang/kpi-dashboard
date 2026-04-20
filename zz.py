import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo KPI", layout="wide", initial_sidebar_state="collimport streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS (GIỮ NGUYÊN)
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

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU (GIỮ NGUYÊN LOGIC)
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
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
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
            elif "not ready" in str(res.get("msg")).lower():
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else:
                return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception as e:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    if not res_data:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v:
                      return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except:
            return np.nan

    weekly_col_idxs = [3, 4, 5, 6] 
    date_row_idx = 3 
    start_col_idx = -1
    for c in range(2, len(vals[date_row_idx])):
        val = str(vals[date_row_idx][c]).strip()
        if val == "1":
            start_col_idx = c
            break
    num_days = 26 
    if start_col_idx != -1:
        max_day = 1
        for c in range(start_col_idx, len(vals[date_row_idx])):
            val = str(vals[date_row_idx][c]).strip()
            if val.isdigit():
                max_day = max(max_day, int(val))
        num_days = max_day
    else:
        start_col_idx = 6
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
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan] 
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        lh_c_list = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_to_scan]
        lh_t_list = [clean_val(lht_idx, c) if pd.notna(clean_val(lht_idx, c)) else 0 for c in cols_to_scan]
        sh_c_list = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_to_scan]
        sh_t_list = [clean_val(sht_idx, c) if pd.notna(clean_val(sht_idx, c)) else 0 for c in cols_to_scan]
        
        data["LH Tổng"] = [c if c > 0 else np.nan for c in lh_c_list]
        data["LH Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(lh_c_list, lh_t_list)]
        data["LH Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(lh_c_list, lh_t_list)]
        
        data["Shuttle Tổng"] = [c if c > 0 else np.nan for c in sh_c_list]
        data["Shuttle Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(sh_c_list, sh_t_list)]
        data["Shuttle Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(sh_c_list, sh_t_list)]

        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1
        
        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            tre = 0 if pd.isna(tre) else tre
            return ((chuyen - tre) / chuyen) * 100
            
        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0, "pw_vin": clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_vout": clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0, "pw_vout": clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_win": clean_val(win_idx, cw_idx) if cw_idx != -1 else 0, "pw_win": clean_val(win_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_wout": clean_val(wout_idx, cw_idx) if wout_idx != -1 else 0, "pw_wout": clean_val(wout_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_tproc_vol": clean_val(tproc_vol_idx, cw_idx) if cw_idx != -1 else 0, "pw_tproc_vol": clean_val(tproc_vol_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_tproc_wgt": clean_val(tproc_wgt_idx, cw_idx) if cw_idx != -1 else 0, "pw_tproc_wgt": clean_val(tproc_wgt_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_ms": clean_val(ms_idx, cw_idx) if cw_idx != -1 else 0, "pw_ms": clean_val(ms_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_bl": clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0, "pw_bl": clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
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

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    if diff > 0:
        bg_color, text_color, sign = "#dcfce7", "#15803d", "+"
        if inverse: bg_color, text_color = "#fee2e2", "#b91c1c"
    elif diff < 0:
        bg_color, text_color, sign = "#fee2e2", "#b91c1c", ""
        if inverse: bg_color, text_color = "#dcfce7", "#15803d"
    else:
        bg_color, text_color, sign = "transparent", "#333", ""
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    return f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'>{wow_str}</td><td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    t_vin = df['Inbound Vol'].sum(skipna=True) 
    t_vout = df['Outbound Vol'].sum(skipna=True) 
    t_tproc_vol = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt = df['Total Process Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    
    lh_t_sum = df['LH Tổng'].sum()
    sh_t_sum = df['Shuttle Tổng'].sum()
    lhot_mtd = (df['LH Đúng Giờ'].sum() / lh_t_sum * 100) if lh_t_sum > 0 else 0
    shot_mtd = (df['Shuttle Đúng Giờ'].sum() / sh_t_sum * 100) if sh_t_sum > 0 else 0
    
    cw = summary
    # 1. METRICS
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Outbound (MTD)", format_vietnam(t_vout))
    c3.metric("Xử lý (MTD)", format_vietnam(t_tproc_vol))
    c4.metric("Trọng lượng (MTD)", format_vietnam(t_tproc_wgt))
    c5.metric("Missort (MTD)", format_vietnam(t_ms))
    c6.metric("Backlog (MTD)", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. WOW TABLE
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(cw['cw_vin'], cw['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(cw['cw_vout'], cw['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(cw['cw_ms'], cw['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(cw['cw_bl'], cw['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td><td class="col-metric">LH Đúng Giờ (%)</td>{get_wow_cell(cw['cw_lhot'], cw['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(cw['cw_shot'], cw['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # 3. BIỂU ĐỒ SẢN LƯỢNG & NĂNG SUẤT (GIỮ NGUYÊN)
    st.markdown(f"<h4 style='color: {primary_color};'>1. Biểu Đồ Sản Lượng & Năng Suất (Số đơn vs Trọng lượng)</h4>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', mode='lines+text', text=[format_vietnam(v) if v > 2000 else "" for v in df['Inbound Vol']], textposition="top center", line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_vol, use_container_width=True)
    with col2:
        st.plotly_chart(px.bar(df, x='Ngày', y='Total Process Vol', title="Năng suất (Số đơn)", text_auto='.2s').update_layout(plot_bgcolor='white'), use_container_width=True)
    with col3:
        st.plotly_chart(px.bar(df, x='Ngày', y='Total Process Wgt', title="Năng suất (Kg)", text_auto='.2s').update_layout(plot_bgcolor='white'), use_container_width=True)

    # 4. BIỂU ĐỒ VẬN TẢI & HÀNG TỒN (ĐÃ FIX THEO DASHBOARD MẪU)
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    
    # HÀNG 2: TỔNG SỐ CHUYẾN (SO SÁNH LH VÀ SHUTTLE)
    fig_total = go.Figure()
    fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['LH Tổng'], name="Linehaul", marker_color='#10b981', text=df['LH Tổng'], textposition='outside'))
    fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Tổng'], name="Shuttle", marker_color='#3b82f6', text=df['Shuttle Tổng'], textposition='outside'))
    fig_total.update_layout(title="Tổng số chuyến xe trong ngày (LH vs Shuttle)", barmode='group', plot_bgcolor='white', height=400, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_total, use_container_width=True)

    # HÀNG 3: CHI TIẾT TRỄ & BACKLOG (3 CỘT)
    c_t1, c_t2, c_bl = st.columns(3)
    with c_t1:
        st.plotly_chart(px.bar(df, x='Ngày', y='LH Trễ', title="Tổng chuyến Linehaul TRỄ", text_auto=True).update_traces(marker_color='#ef4444').update_layout(plot_bgcolor='white', height=300), use_container_width=True)
    with c_t2:
        st.plotly_chart(px.bar(df, x='Ngày', y='Shuttle Trễ', title="Tổng chuyến Shuttle TRỄ", text_auto=True).update_traces(marker_color='#f43f5e').update_layout(plot_bgcolor='white', height=300), use_container_width=True)
    with c_bl:
        st.plotly_chart(px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text_auto=True).update_traces(marker_color='#f59e0b').update_layout(plot_bgcolor='white', height=300), use_container_width=True)

    with st.expander("🔍 Chi tiết dữ liệu thô"):
        st.dataframe(df.set_index("Ngày").T, use_container_width=True)

with tab1:
    render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669")apsed")

# CSS đơn giản, chuyên nghiệp
st.markdown("""
<style>
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        font-size: 16px; 
        font-weight: 600; 
        padding: 12px 24px;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] { color: #dc2626 !important; border-bottom: 3px solid #dc2626 !important; }
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="metric-container"] label { font-size: 14px !important; color: #64748b !important; font-weight: 500 !important; }
    div[data-testid="metric-container"] div { font-size: 28px !important; color: #1e293b !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU
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
    if not token:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}

    for _ in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                break
            time.sleep(2)
        except:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v: 
                    return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except:
            return np.nan

    weekly_col_idxs = [3, 4, 5, 6] 
    date_row_idx = 3 
    start_col_idx = -1

    for c in range(2, len(vals[date_row_idx])):
        if str(vals[date_row_idx][c]).strip() == "1":
            start_col_idx = c
            break
    if start_col_idx == -1:
        start_col_idx = 6

    num_days = 26 
    max_day = 1
    for c in range(start_col_idx, len(vals[date_row_idx])):
        val = str(vals[date_row_idx][c]).strip()
        if val.isdigit():
            max_day = max(max_day, int(val))
    num_days = max_day
    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"{i+1}" for i in range(num_days)]}
        data["Inbound"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Process"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
        data["Weight"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]

        lh_c = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_to_scan]
        lh_t = [clean_val(lht_idx, c) if pd.notna(clean_val(lht_idx, c)) else 0 for c in cols_to_scan]
        sh_c = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_to_scan]
        sh_t = [clean_val(sht_idx, c) if pd.notna(clean_val(sht_idx, c)) else 0 for c in cols_to_scan]

        data["LH_OK"] = [(c - t) if c > 0 else 0 for c, t in zip(lh_c, lh_t)]
        data["LH_Late"] = [t if t > 0 else 0 for c, t in zip(lh_c, lh_t)]
        data["SH_OK"] = [(c - t) if c > 0 else 0 for c, t in zip(sh_c, sh_t)]
        data["SH_Late"] = [t if t > 0 else 0 for c, t in zip(sh_c, sh_t)]

        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            return ((chuyen - (tre if pd.notna(tre) else 0)) / chuyen) * 100

        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0, 
            "pw_vin": clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_vout": clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0, 
            "pw_vout": clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_ms": clean_val(ms_idx, cw_idx) if cw_idx != -1 else 0, 
            "pw_ms": clean_val(ms_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_bl": clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0, 
            "pw_bl": clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), 
            "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), 
            "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)

    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h1 style='text-align: center; font-size: 32px; font-weight: 800; color: #dc2626; margin-bottom: 8px;'>J&T CARGO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px; color: #64748b; margin-bottom: 32px;'>KPI Dashboard</p>", unsafe_allow_html=True)

data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu...")
    st.stop()

tab1, tab2 = st.tabs(["Hồ Chí Minh Hub", "Bắc Ninh Hub"])

def fmt(num):
    if pd.isna(num): return "0"
    return f"{int(num):,}".replace(",", ".")

def render_dashboard(df, summary):
    # METRICS
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound", fmt(df['Inbound'].sum()))
    c2.metric("Outbound", fmt(df['Outbound'].sum()))
    c3.metric("Xử lý", fmt(df['Process'].sum()))
    c4.metric("Trọng lượng", fmt(df['Weight'].sum()))
    c5.metric("Missort", fmt(df['Missort'].sum()), delta=f"{(df['Missort'].sum()/df['Process'].sum()*100):.1f}%" if df['Process'].sum() > 0 else "0%")
    c6.metric("Backlog", fmt(df['Backlog'].sum()))

    # CHART 1: Inbound/Outbound Trend
    st.markdown("<h3 style='font-size: 18px; font-weight: 600; color: #1e293b; margin-top: 32px; margin-bottom: 16px;'>Xu hướng Inbound & Outbound</h3>", unsafe_allow_html=True)
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df['Ngày'], y=df['Inbound'],
        mode='lines+markers',
        name='Inbound',
        line=dict(color='#dc2626', width=3),
        marker=dict(size=8, color='#dc2626', line=dict(width=2, color='white')),
        fill='tozeroy',
        fillcolor='rgba(220, 38, 38, 0.1)'
    ))
    fig1.add_trace(go.Scatter(
        x=df['Ngày'], y=df['Outbound'],
        mode='lines+markers',
        name='Outbound',
        line=dict(color='#ea580c', width=3),
        marker=dict(size=8, color='#ea580c', line=dict(width=2, color='white'))
    ))
    fig1.update_layout(
        height=380,
        margin=dict(t=20, b=40, l=60, r=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center', font=dict(size=13)),
        xaxis=dict(
            title="Ngày",
            titlefont=dict(size=13, color='#64748b'),
            tickfont=dict(size=12, color='#64748b'),
            showgrid=False,
            linecolor='#e2e8f0',
            linewidth=2
        ),
        yaxis=dict(
            title="Số đơn",
            titlefont=dict(size=13, color='#64748b'),
            tickfont=dict(size=12, color='#64748b'),
            showgrid=True,
            gridcolor='#f1f5f9',
            gridwidth=1,
            linecolor='#e2e8f0',
            linewidth=2
        ),
        hovermode='x unified'
    )
    st.plotly_chart(fig1, use_container_width=True)

    # CHART 2: Productivity
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h3 style='font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 16px;'>Năng suất xử lý (Đơn)</h3>", unsafe_allow_html=True)
        avg_val = df['Process'].mean()
        colors = ['#dc2626' if v >= avg_val else '#94a3b8' for v in df['Process']]
        
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df['Ngày'],
            y=df['Process'],
            marker_color=colors,
            text=[fmt(v) for v in df['Process']],
            textposition='outside',
            textfont=dict(size=12, color='#1e293b'),
            marker_line_width=0
        ))
        fig2.add_hline(y=avg_val, line_dash="dash", line_color="#dc2626", line_width=2,
                      annotation_text=f"Trung bình: {fmt(avg_val)}",
                      annotation_position="top right",
                      annotation_font=dict(size=12, color='#dc2626'))
        fig2.update_layout(
            height=320,
            margin=dict(t=30, b=40, l=60, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(tickfont=dict(size=11, color='#64748b'), showgrid=False),
            yaxis=dict(tickfont=dict(size=11, color='#64748b'), showgrid=True, gridcolor='#f1f5f9'),
            bargap=0.35,
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        st.markdown("<h3 style='font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 16px;'>Năng suất (Kg)</h3>", unsafe_allow_html=True)
        avg_wgt = df['Weight'].mean()
        colors2 = ['#ea580c' if v >= avg_wgt else '#94a3b8' for v in df['Weight']]
        
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=df['Ngày'],
            y=df['Weight'],
            marker_color=colors2,
            text=[f"{v/1000:.0f}k" if v >= 1000 else fmt(v) for v in df['Weight']],
            textposition='outside',
            textfont=dict(size=12, color='#1e293b'),
            marker_line_width=0
        ))
        fig3.add_hline(y=avg_wgt, line_dash="dash", line_color="#ea580c", line_width=2,
                      annotation_text=f"TB: {fmt(avg_wgt)}",
                      annotation_position="top right",
                      annotation_font=dict(size=12, color='#ea580c'))
        fig3.update_layout(
            height=320,
            margin=dict(t=30, b=40, l=60, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(tickfont=dict(size=11, color='#64748b'), showgrid=False),
            yaxis=dict(tickfont=dict(size=11, color='#64748b'), showgrid=True, gridcolor='#f1f5f9'),
            bargap=0.35,
            showlegend=False
        )
        st.plotly_chart(fig3, use_container_width=True)

    # CHART 3: Transport & Quality
    st.markdown("<h3 style='font-size: 18px; font-weight: 600; color: #1e293b; margin-top: 24px; margin-bottom: 16px;'>Vận tải & Chất lượng</h3>", unsafe_allow_html=True)
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=df['Ngày'], y=df['LH_OK'], name='Đúng giờ', marker_color='#16a34a',
                             text=[str(int(v)) if v > 0 else "" for v in df['LH_OK']], 
                             textposition='inside', textfont=dict(size=11, color='white')))
        fig4.add_trace(go.Bar(x=df['Ngày'], y=df['LH_Late'], name='Trễ', marker_color='#dc2626',
                             text=[str(int(v)) if v > 0 else "" for v in df['LH_Late']], 
                             textposition='inside', textfont=dict(size=11, color='white')))
        fig4.update_layout(
            title=dict(text='Linehaul', font=dict(size=14, color='#1e293b')),
            height=280,
            barmode='stack',
            margin=dict(t=40, b=30, l=40, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor='center', font=dict(size=10)),
            xaxis=dict(tickfont=dict(size=10, color='#64748b'), showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color='#64748b'), showgrid=True, gridcolor='#f1f5f9'),
            bargap=0.3
        )
        st.plotly_chart(fig4, use_container_width=True)
    
    with col4:
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(x=df['Ngày'], y=df['SH_OK'], name='Đúng giờ', marker_color='#0891b2',
                             text=[str(int(v)) if v > 0 else "" for v in df['SH_OK']], 
                             textposition='inside', textfont=dict(size=11, color='white')))
        fig5.add_trace(go.Bar(x=df['Ngày'], y=df['SH_Late'], name='Trễ', marker_color='#f59e0b',
                             text=[str(int(v)) if v > 0 else "" for v in df['SH_Late']], 
                             textposition='inside', textfont=dict(size=11, color='white')))
        fig5.update_layout(
            title=dict(text='Shuttle', font=dict(size=14, color='#1e293b')),
            height=280,
            barmode='stack',
            margin=dict(t=40, b=30, l=40, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor='center', font=dict(size=10)),
            xaxis=dict(tickfont=dict(size=10, color='#64748b'), showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color='#64748b'), showgrid=True, gridcolor='#f1f5f9'),
            bargap=0.3
        )
        st.plotly_chart(fig5, use_container_width=True)
    
    with col5:
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            x=df['Ngày'], 
            y=df['Backlog'], 
            marker_color='#7c3aed',
            text=[str(int(v)) if v > 0 else "" for v in df['Backlog']], 
            textposition='outside',
            textfont=dict(size=11, color='#1e293b')
        ))
        fig6.update_layout(
            title=dict(text='Backlog', font=dict(size=14, color='#1e293b')),
            height=280,
            margin=dict(t=40, b=30, l=40, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(tickfont=dict(size=10, color='#64748b'), showgrid=False),
            yaxis=dict(tickfont=dict(size=10, color='#64748b'), showgrid=True, gridcolor='#f1f5f9'),
            bargap=0.3,
            showlegend=False
        )
        st.plotly_chart(fig6, use_container_width=True)

    with st.expander("📋 Xem dữ liệu chi tiết"):
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab1:
    render_dashboard(df_hcm, sum_hcm)
with tab2:
    render_dashboard(df_bn, sum_bn)
