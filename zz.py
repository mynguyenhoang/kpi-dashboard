import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .kpi-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
        background-color: white;
    }
    .kpi-table th {
        background-color: #1f2937;
        color: white;
        padding: 10px;
        text-align: center;
        border: 1px solid #d1d5db;
    }
    .kpi-table td {
        padding: 10px;
        border: 1px solid #d1d5db;
        text-align: right;
    }
    .col-metric { font-weight: 600; text-align: left !important; }
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
    if not token: return pd.DataFrame(), pd.DataFrame()
    
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
        if not vals or len(vals) < 55: return pd.DataFrame(), pd.DataFrame()

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

        # Tự động xác định số ngày có dữ liệu (để tính MTD không bị cộng dồn số 0 của tương lai)
        date_row_idx = 3
        start_col_idx = 6 # Mặc định
        for c in range(2, len(vals[date_row_idx])):
            if str(vals[date_row_idx][c]).strip() == "1":
                start_col_idx = c
                break
        
        # Xác định ngày hiện tại dựa trên ô có dữ liệu Inbound thực tế
        num_days = 0
        for i in range(31):
            if pd.notna(clean_val(8, start_col_idx + i)): num_days = i + 1
            else: break
        
        if num_days == 0: num_days = 26 # Fallback

        cols_to_scan = [start_col_idx + i for i in range(num_days)]

        def extract_hub_data(vol_idx, wgt_idx, ms_idx, ms_rt_idx, bl_idx, c_idxs, t_idxs):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
            data["Vol"] = [clean_val(vol_idx, c) for c in cols_to_scan]
            data["Wgt"] = [clean_val(wgt_idx, c) for c in cols_to_scan]
            data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
            data["Missort_Rate"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
            data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
            
            # Xử lý xe COT
            c_list = [sum(filter(None, [clean_val(r, col) for r in c_idxs])) for col in cols_to_scan]
            t_list = [sum(filter(None, [clean_val(r, col) for r in t_idxs])) for col in cols_to_scan]
            data["Xe_Dung"] = [(c - t) if c > 0 else np.nan for c, t in zip(c_list, t_list)]
            data["Xe_Tre"] = [t if c > 0 else np.nan for c, t in zip(c_list, t_list)]
            return pd.DataFrame(data)

        df_hcm = extract_hub_data(8, 9, 17, 18, 31, [38, 39], [40, 41])
        df_bn = extract_hub_data(14, 15, 19, 20, 32, [47, 48], [49, 50])
        return df_hcm, df_bn
    except: return pd.DataFrame(), pd.DataFrame()

# 3. GIAO DIỆN
st.markdown("<h1 style='text-align: center; color: #0f172a;'>📊 J&T CARGO KPI DASHBOARD</h1>", unsafe_allow_html=True)
df_hcm, df_bn = get_data()

def format_vn(n):
    if pd.isna(n): return "0"
    return f"{n:,.0f}".replace(",", ".")

def render_hub(df, color):
    if df.empty:
        st.warning("Không có dữ liệu.")
        return

    # TÍNH TOÁN MTD (Chỉ tính trên số ngày đã có dữ liệu)
    m_vol = df['Vol'].sum()
    m_wgt = df['Wgt'].sum()
    m_ms = df['Missort'].sum()
    m_bl = df.iloc[-1]['Backlog'] if not df.empty else 0 # Backlog lấy ngày cuối cùng
    
    m_xe_dung = df['Xe_Dung'].sum(skipna=True)
    m_xe_tong = m_xe_dung + df['Xe_Tre'].sum(skipna=True)
    m_ot_rate = (m_xe_dung / m_xe_tong * 100) if m_xe_tong > 0 else 0
    m_ms_rate = (m_ms / m_vol * 100) if m_vol > 0 else 0

    # Hiển thị Metric
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Sản Lượng (MTD)", format_vn(m_vol))
    c2.metric("⚖️ Trọng Lượng (MTD)", format_vn(m_wgt) + " kg")
    c3.metric("❌ Missort (MTD)", format_vn(m_ms), f"{m_ms_rate:.2f}%")
    c4.metric("🕒 Backlog (Hiện tại)", format_vn(m_bl))
    c5.metric("🚚 LH Đúng Giờ (MTD)", f"{m_ot_rate:.2f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # BIỂU ĐỒ
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.area(df, x="Ngày", y="Vol", title="Xu hướng Sản lượng hàng ngày")
        fig1.update_traces(line_color=color, fillcolor='rgba(14, 165, 233, 0.1)')
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Số đơn Missort", marker_color='#94a3b8'), secondary_y=False)
        fig2.add_trace(go.Scatter(x=df['Ngày'], y=df['Missort_Rate'], name="Tỷ lệ %", line=dict(color='#ef4444')), secondary_y=True)
        fig2.update_layout(title="Phân tích Missort")
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df['Ngày'], y=df['Xe_Dung'], name="Đúng giờ", marker_color='#10b981'))
        fig3.add_trace(go.Bar(x=df['Ngày'], y=df['Xe_Tre'], name="Trễ", marker_color='#f43f5e'))
        fig3.update_layout(title="Kiểm soát Chuyến xe COT", barmode='stack')
        st.plotly_chart(fig3, use_container_width=True)
    with col4:
        fig4 = px.bar(df, x="Ngày", y="Backlog", title="Theo dõi Backlog tồn đọng", color_discrete_sequence=['#f59e0b'])
        st.plotly_chart(fig4, use_container_width=True)

    with st.expander("🔍 Xem bảng dữ liệu chi tiết"):
        st.dataframe(df.set_index("Ngày").T, use_container_width=True)

tab1, tab2 = st.tabs(["🏢 HỒ CHÍ MINH HUB", "🏢 BẮC NINH HUB"])
with tab1: render_hub(df_hcm, "#0ea5e9")
with tab2: render_hub(df_bn, "#059669")
