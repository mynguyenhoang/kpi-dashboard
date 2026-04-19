import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG (Để chế độ Wide cho rộng rãi)
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Thêm một chút CSS tùy chỉnh để làm đẹp các thẻ Metric
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỰ ĐỘNG TỪ FEISHU (GIỮ NGUYÊN)
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
        st.error("❌ Không lấy được Token Feishu. Hãy kiểm tra lại APP_ID/SECRET.")
        return pd.DataFrame(), pd.DataFrame()

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        if res.get("code") != 0:
            st.error(f"❌ Lỗi Feishu: {res.get('msg')}")
            return pd.DataFrame(), pd.DataFrame()

        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
        if not vals or len(vals) < 65:
            return pd.DataFrame(), pd.DataFrame()

        def clean_val(row_idx, col_idx):
            try:
                if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                    v = vals[row_idx][col_idx]
                    if v is None or str(v).strip() == "" or any(err in str(v) for err in ["IF(", "=", "#N/A", "#ERROR"]): 
                        return np.nan
                    s = str(v).replace('%', '').replace(',', '').strip()
                    if s == '-': return 0
                    return float(s)
                return np.nan
            except:
                return np.nan

        START_COL = 4 
        for col_idx in range(2, len(vals[8])):
            val = str(vals[8][col_idx]).strip()
            if val and val.replace(',', '').replace('.', '').isdigit():
                START_COL = col_idx
                break

        num_days = 0
        for col_idx in range(len(vals[8]) - 1, START_COL - 1, -1):
            val = str(vals[8][col_idx]).strip()
            if val and "IF(" not in val and "#" not in val and val != "":
                num_days = col_idx - START_COL + 1
                break

        if num_days <= 0: num_days = 1
        cols_to_scan = [START_COL + i for i in range(num_days)]

        def extract_hub_data(vol_idx, wgt_idx, ms_idx, ms_rt_idx, fte_idx, bl_idx, chuyen_idxs, tre_idxs, lh_rt_idx):
            data = {
                "Ngày": [f"Ngày {i+1}" for i in range(num_days)], # Thêm chữ "Ngày" cho đẹp trục X
                "Tổng lượng hàng": [clean_val(vol_idx, c) for c in cols_to_scan],
                "Tổng trọng lượng (Kg)": [clean_val(wgt_idx, c) for c in cols_to_scan],
                "Số đơn Missort": [clean_val(ms_idx, c) for c in cols_to_scan],
                "Tỷ lệ Missort (%)": [clean_val(ms_rt_idx, c) for c in cols_to_scan],
                "Tổng nhân sự": [clean_val(fte_idx, c) for c in cols_to_scan],
                "Backlog tồn đọng": [clean_val(bl_idx, c) for c in cols_to_scan],
                "Xe Sai COT (Tổng)": [
                    sum(filter(pd.notna, [clean_val(r, c) for r in tre_idxs])) if any(pd.notna(clean_val(r, c)) for r in tre_idxs) else np.nan 
                    for c in cols_to_scan
                ],
                "Xe Đúng COT (Tổng)": [
                    sum(filter(pd.notna, [clean_val(r, c) for r in chuyen_idxs])) - sum(filter(pd.notna, [clean_val(r, c) for r in tre_idxs]))
                    if any(pd.notna(clean_val(r, c)) for r in chuyen_idxs) else np.nan 
                    for c in cols_to_scan
                ],
                "Tỷ lệ Linehaul đúng giờ (%)": [clean_val(lh_rt_idx, c) for c in cols_to_scan]
            }
            return pd.DataFrame(data)

        # HCM HUB 
        df_hcm = extract_hub_data(13, 14, 19, 20, 27, 35, [45, 46], [47, 48], 51)
        # BN HUB 
        df_bn = extract_hub_data(21, 22, 23, 24, 31, 38, [56, 57], [58, 59], 62)
        
        return df_hcm, df_bn
        
    except Exception as e:
        st.error(f"❌ Lỗi hệ thống: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# 3. GIAO DIỆN HIỂN THỊ CHUNG
st.markdown("<h1 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>📊 J&T CARGO KPI DASHBOARD</h1>", unsafe_allow_html=True)
df_hcm, df_bn = get_data()

if df_hcm.empty and df_bn.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu.")
    st.stop()

tab1, tab2 = st.tabs(["🏢 HỒ CHÍ MINH HUB", "🏢 BẮC NINH HUB"])

# HÀM RENDER BIỂU ĐỒ ĐÃ ĐƯỢC LÀM ĐẸP (NÂNG CẤP)
def render_dashboard(df, primary_color):
    if df.empty:
        st.info("Chưa có dữ liệu cho Hub này.")
        return

    # TÍNH TOÁN HEADER METRICS
    total_vol = df['Tổng lượng hàng'].sum() 
    total_weight = df['Tổng trọng lượng (Kg)'].sum()
    total_missort = df['Số đơn Missort'].sum()
    total_backlog = df['Backlog tồn đọng'].sum()
    total_man_days = df['Tổng nhân sự'].sum()

    working_days = 26 
    header_pcs_month = (total_vol / total_man_days * working_days) if total_man_days > 0 else 0
    header_kg_month = (total_weight / total_man_days * working_days) if total_man_days > 0 else 0

    total_xe_dung = df['Xe Đúng COT (Tổng)'].sum()
    total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum()
    final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0
    final_missort_rate = (total_missort / total_vol * 100) if total_vol > 0 else 0

    # KHUNG HIỂN THỊ KPI TRÊN CÙNG
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Tổng Sản Lượng", f"{int(total_vol):,}".replace(",", "."))
    c2.metric("⚖️ Tổng Trọng Lượng", f"{int(total_weight):,}".replace(",", ".") + " kg")
    c3.metric("❌ Tổng Missort", f"{int(total_missort):,}", f"{final_missort_rate:.2f}% tỷ lệ")
    c4.metric("📦 Tổng Backlog", f"{int(total_backlog):,}")
    c5.metric("🚚 Tỷ Lệ LH Đúng Giờ", f"{final_ontime_rate:.2f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # DÒNG CHART 1: SẢN LƯỢNG VÀ MISSORT
    st.markdown(f"<h4 style='color: {primary_color};'>1. Đánh giá Sản Lượng & Chất Lượng Phân Loại (Missort)</h4>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # BIỂU ĐỒ SẢN LƯỢNG (AREA CHART MỀM MẠI)
        fig_vol = px.area(df, x="Ngày", y="Tổng lượng hàng", title="Biểu đồ Sản lượng hàng ngày")
        fig_vol.update_traces(line_color=primary_color, fillcolor='rgba(56, 189, 248, 0.2)', mode='lines+markers+text', 
                              text=[f"{v:g}" if pd.notna(v) else "" for v in df['Tổng lượng hàng']], textposition="top center")
        fig_vol.update_layout(plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10))
        fig_vol.update_xaxes(showgrid=False)
        fig_vol.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_chart2:
        # BIỂU ĐỒ KẾP HỢP MISSORT: Cột (Số đơn) + Đường (Tỷ lệ %)
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Số đơn Missort'], name="Số đơn Missort", marker_color='#94a3b8', opacity=0.7), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
        fig_ms.update_layout(title_text="Phân tích Missort (Số lượng & Tỷ lệ)", plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_ms.update_xaxes(showgrid=False)
        fig_ms.update_yaxes(showgrid=True, gridcolor='#f1f5f9', secondary_y=False)
        st.plotly_chart(fig_ms, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # DÒNG CHART 2: VẬN TẢI & TỒN KHO
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải (Linehaul) & Hàng Tồn (Backlog)</h4>", unsafe_allow_html=True)
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        # BIỂU ĐỒ KIỂM SOÁT COT (STACKED BAR CHART LÊN MÀU ĐẸP)
        fig_xe = go.Figure()
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['Xe Đúng COT (Tổng)'], name="Đúng giờ COT", marker_color='#10b981')) # Xanh ngọc
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['Xe Sai COT (Tổng)'], name="Trễ giờ COT", marker_color='#f43f5e')) # Đỏ hồng
        fig_xe.update_layout(title="Kiểm soát Chuyến xe chạy COT", barmode='stack', plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_xe.update_xaxes(showgrid=False)
        fig_xe.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_xe, use_container_width=True)

    with col_chart4:
        # BIỂU ĐỒ TỒN KHO (BACKLOG BAR CHART)
        fig_bl = px.bar(df, x="Ngày", y="Backlog tồn đọng", title="Backlog tồn đọng cuối ngày")
        fig_bl.update_traces(marker_color='#f59e0b', text=[f"{v:g}" if pd.notna(v) else "" for v in df['Backlog tồn đọng']], textposition="outside") # Màu vàng cam
        fig_bl.update_layout(plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10))
        fig_bl.update_xaxes(showgrid=False)
        fig_bl.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_bl, use_container_width=True)

    # BẢNG DATA RAW RÚT GỌN NẰM BÊN DƯỚI
    with st.expander("🔍 Bảng đối soát dữ liệu thô"):
        df_show = df.set_index("Ngày").T
        df_show = df_show.fillna("")
        st.dataframe(df_show, use_container_width=True)

# 4. GỌI HÀM VẼ GIAO DIỆN CHO TỪNG TAB (Chỉnh màu Chủ đạo)
with tab1:
    render_dashboard(df_hcm, primary_color="#0ea5e9") # Màu xanh dương nhạt cho HCM
with tab2:
    render_dashboard(df_bn, primary_color="#059669")  # Màu xanh lá đậm cho BN
