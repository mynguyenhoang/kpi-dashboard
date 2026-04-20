import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# 1. CẤU HÌNH TRANG & CSS NÂNG CAO
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Tổng thể */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main { background-color: #f1f5f9; }
    
    /* Thiết kế Metric Card mới */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        border-top: 4px solid #ef4444; /* Màu đỏ thương hiệu J&T */
    }
    .metric-label { font-size: 14px; color: #64748b; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 32px; color: #1e293b; font-weight: 800; margin: 5px 0; }
    
    /* Bảng KPI - To và rõ hơn */
    .kpi-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background-color: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 25px;
    }
    .kpi-table th {
        background-color: #1e293b;
        color: white;
        padding: 15px;
        font-size: 16px;
        text-transform: uppercase;
    }
    .kpi-table td {
        padding: 15px;
        font-size: 16px; /* Tăng size số trong bảng */
        border-bottom: 1px solid #e2e8f0;
    }
    .col-mtd { font-weight: 800; color: #0f172a; background-color: #f8fafc; font-size: 18px !important; }
    
    /* Plotly Chart Container */
    .chart-container {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU (Giữ nguyên logic của bạn nhưng thêm xử lý lỗi)
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
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    if not vals: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            v = vals[row_idx][col_idx]
            s = str(v).replace('%', '').replace(',', '').strip()
            return float(s) if s not in ["", "-", "None"] else 0.0
        except: return 0.0

    # Logic lấy ngày và số cột (rút gọn để tập trung vào UI)
    num_days = 26 
    cols_to_scan = [6 + i for i in range(num_days)]
    weekly_col_idxs = [3, 4, 5, 6]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"D{i+1}" for i in range(num_days)]} # Rút ngắn "Ngày" thành "D" cho đỡ chật biểu đồ
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
        data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        data["LH Đúng Giờ"] = [clean_val(lhc_idx, c) - clean_val(lht_idx, c) for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Đúng Giờ"] = [clean_val(shc_idx, c) - clean_val(sht_idx, c) for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        cw_idx = weekly_col_idxs[-1]
        pw_idx = weekly_col_idxs[-2]
        
        def get_ot_rate(c_idx, t_idx, col_idx):
            c = clean_val(c_idx, col_idx)
            t = clean_val(t_idx, col_idx)
            return ((c - t) / c * 100) if c > 0 else 0

        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. HELPER UI
def ui_metric_card(label, value):
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

def format_vn(n):
    return f"{n:,.0f}".replace(",", ".")

def get_wow_html(cur, prev, is_pct=False, inverse=False):
    if prev == 0: return "<td>-</td><td>-</td><td>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff/prev*100)
    color = "#15803d" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#b91c1c"
    arrow = "↑" if diff > 0 else "↓"
    
    cur_s = f"{cur:.1f}%" if is_pct else format_vn(cur)
    prev_s = f"{prev:.1f}%" if is_pct else format_vn(prev)
    
    return f"""
        <td style="color:{color}; font-weight:bold; text-align:center;">{arrow} {abs(pct):.0f}%</td>
        <td class="col-num" style="font-weight:600;">{cur_s}</td>
        <td class="col-num" style="color:#64748b;">{prev_s}</td>
    """

# 4. RENDER DASHBOARD
data_hcm, data_bn = get_data()

st.markdown("<h1 style='text-align: center; color: #1e293b; padding: 20px;'>🚚 J&T CARGO KPI OPERATIONAL</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📍 HỒ CHÍ MINH HUB", "📍 BẮC NINH HUB"])

def render_hub(df, summary):
    # Top Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: ui_metric_card("Inbound MTD", format_vn(df['Inbound Vol'].sum()))
    with m2: ui_metric_card("Xử lý MTD", format_vn(df['Total Process Vol'].sum()))
    with m3: ui_metric_card("Trọng lượng (kg)", format_vn(df['Total Process Wgt'].sum()))
    with m4: ui_metric_card("Missort", format_vn(df['Missort'].sum()))
    with m5: ui_metric_card("Backlog", format_vn(df['Backlog'].max()))
    
    st.write("---")
    
    # Bảng WOW
    st.markdown(f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>Phân nhóm KPI</th><th>Chỉ số</th><th>Biến động (WoW)</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th>
            </tr>
        </thead>
        <tbody>
            <tr><td rowspan="2" style="font-weight:bold; background:#f1f5f9; text-align:center;">SẢN LƯỢNG</td>
                <td>Inbound (Đơn)</td>{get_wow_html(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vn(df['Inbound Vol'].sum())}</td></tr>
            <tr><td>Outbound (Đơn)</td>{get_wow_html(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vn(df['Outbound Vol'].sum())}</td></tr>
            <tr><td rowspan="2" style="font-weight:bold; background:#f1f5f9; text-align:center;">CHẤT LƯỢNG</td>
                <td>Missort (Đơn)</td>{get_wow_html(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vn(df['Missort'].sum())}</td></tr>
            <tr><td>Backlog (Đơn)</td>{get_wow_html(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vn(df['Backlog'].max())}</td></tr>
            <tr><td rowspan="2" style="font-weight:bold; background:#f1f5f9; text-align:center;">VẬN TẢI</td>
                <td>LH Đúng Giờ</td>{get_wow_html(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{(df['LH Đúng Giờ'].sum()/(df['LH Đúng Giờ'].sum()+df['LH Trễ'].sum())*100):.1f}%</td></tr>
            <tr><td>Shuttle Đúng Giờ</td>{get_wow_html(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{(df['Shuttle Đúng Giờ'].sum()/(df['Shuttle Đúng Giờ'].sum()+df['Shuttle Trễ'].sum())*100):.1f}%</td></tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    # Biểu đồ
    c1, c2 = st.columns(2)
    with c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", line=dict(width=4, color='#3b82f6'), fill='tozeroy'))
        fig1.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], name="Xử lý", marker_color='#94a3b8', opacity=0.5))
        fig1.update_layout(title="<b>XU HƯỚNG SẢN LƯỢNG HÀNG NGÀY</b>", hovermode="x unified", height=400,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['LH Đúng Giờ'], name="LH Đúng Giờ", marker_color='#10b981'))
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['LH Trễ'], name="LH Trễ", marker_color='#ef4444'))
        fig2.update_layout(title="<b>TÌNH TRẠNG VẬN TẢI LINEHAUL</b>", barmode='stack', height=400,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig2, use_container_width=True)

with tab1: render_hub(data_hcm[0], data_hcm[1])
with tab2: render_hub(data_bn[0], data_bn[1])
