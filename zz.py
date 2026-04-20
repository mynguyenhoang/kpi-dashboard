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
        
        # SỐ CHUYẾN XE (LH & SH)
        data["LH Chuyến"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
        data["SH Chuyến"] = [clean_val(shc_idx, c) for c in cols_to_scan]
        
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_val_summary(idx, col):
            return clean_val(idx, col) if col != -1 else 0

        weekly_summary = {
            "cw_vin": get_val_summary(vin_idx, cw_idx), "pw_vin": get_val_summary(vin_idx, pw_idx),
            "cw_vout": get_val_summary(vout_idx, cw_idx), "pw_vout": get_val_summary(vout_idx, pw_idx),
            "cw_ms": get_val_summary(ms_idx, cw_idx), "pw_ms": get_val_summary(ms_idx, pw_idx),
            "cw_bl": get_val_summary(bl_idx, cw_idx), "pw_bl": get_val_summary(bl_idx, pw_idx),
            "cw_lh": get_val_summary(lhc_idx, cw_idx), "pw_lh": get_val_summary(lhc_idx, pw_idx),
            "cw_sh": get_val_summary(shc_idx, cw_idx), "pw_sh": get_val_summary(shc_idx, pw_idx),
        }
        return pd.DataFrame(data), weekly_summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    bg_color, text_color, sign = "transparent", "#333", ""
    if diff > 0:
        bg_color, text_color, sign = ("#fee2e2", "#b91c1c", "+") if inverse else ("#dcfce7", "#15803d", "+")
    elif diff < 0:
        bg_color, text_color, sign = ("#dcfce7", "#15803d", "") if inverse else ("#fee2e2", "#b91c1c", "")
    
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    return f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'>{wow_str}</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>{format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # METRICS MTD
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound (MTD)", format_vietnam(df['Inbound Vol'].sum()))
    c2.metric("Outbound (MTD)", format_vietnam(df['Outbound Vol'].sum()))
    c3.metric("Xử lý (MTD)", format_vietnam(df['Total Process Vol'].sum()))
    c4.metric("Trọng lượng (MTD)", format_vietnam(df['Total Process Wgt'].sum()))
    c5.metric("Missort (MTD)", format_vietnam(df['Missort'].sum()))
    c6.metric("Backlog", format_vietnam(df['Backlog'].dropna().iloc[-1] if not df['Backlog'].dropna().empty else 0))
    
    st.markdown("<br>", unsafe_allow_html=True)

    # BẢNG WOW
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(df['Inbound Vol'].sum())}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(df['Outbound Vol'].sum())}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(df['Missort'].sum())}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(df['Backlog'].sum())}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td><td class="col-metric">LH (chuyến)</td>{get_wow_cell(summary['cw_lh'], summary['pw_lh'])}<td class="col-mtd">{format_vietnam(df['LH Chuyến'].sum())}</td></tr>
            <tr><td class="col-metric">Shuttle (chuyến)</td>{get_wow_cell(summary['cw_sh'], summary['pw_sh'])}<td class="col-mtd">{format_vietnam(df['SH Chuyến'].sum())}</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # BIỂU ĐỒ SẢN LƯỢNG & NĂNG SUẤT
    st.markdown(f"<h4 style='color: {primary_color};'>1. Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    col_v1, col_v2, col_v3 = st.columns([1.2, 1, 1])
    with col_v1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', mode='lines', line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Inbound & Outbound hàng ngày", plot_bgcolor='white', height=300, margin=dict(t=40, b=10))
        st.plotly_chart(fig_vol, use_container_width=True)
    with col_v2:
        fig_p1 = px.bar(df, x="Ngày", y="Total Process Vol", title="Năng suất (Đơn)", text_auto='.2s')
        fig_p1.update_traces(marker_color='#38bdf8').update_layout(plot_bgcolor='white', height=300)
        st.plotly_chart(fig_p1, use_container_width=True)
    with col_v3:
        fig_p2 = px.bar(df, x="Ngày", y="Total Process Wgt", title="Năng suất (Kg)", text_auto='.2s')
        fig_p2.update_traces(marker_color='#818cf8').update_layout(plot_bgcolor='white', height=300)
        st.plotly_chart(fig_p2, use_container_width=True)

    # BIỂU ĐỒ VẬN TẢI & BACKLOG
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        # LH: Hiện tổng chuyến lên đầu cột
        fig_lh = px.bar(df, x='Ngày', y='LH Chuyến', title="Linehaul (LH)", text_auto=True)
        fig_lh.update_traces(marker_color='#10b981', textposition='outside')
        fig_lh.update_layout(plot_bgcolor='white', yaxis_title="Số chuyến", height=350)
        st.plotly_chart(fig_lh, use_container_width=True)

    with col_t2:
        # SH: Hiện tổng chuyến lên đầu cột
        fig_sh = px.bar(df, x='Ngày', y='SH Chuyến', title="Shuttle (ST)", text_auto=True)
        fig_sh.update_traces(marker_color='#3b82f6', textposition='outside')
        fig_sh.update_layout(plot_bgcolor='white', yaxis_title="Số chuyến", height=350)
        st.plotly_chart(fig_sh, use_container_width=True)

    with col_t3:
        # Backlog
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text_auto=True)
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        fig_bl.update_layout(plot_bgcolor='white', height=350)
        st.plotly_chart(fig_bl, use_container_width=True)

    with st.expander("🔍 Chi tiết dữ liệu thô"):
        st.dataframe(df.set_index("Ngày").T, use_container_width=True)

# PHÂN TAB HUB
if not data_hcm[0].empty:
    tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
    with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
    with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
