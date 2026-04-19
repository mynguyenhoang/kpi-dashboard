import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide")

# 2. HÀM LẤY DỮ LIỆU TỰ ĐỘNG TỪ FEISHU
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

    # Mở rộng range lên AQ80 để quét tới tận dòng thông số Linehaul của BN HUB
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

        # Dò tìm cột "Ngày 1"
        START_COL = 4 
        for col_idx in range(2, len(vals[8])):
            val = str(vals[8][col_idx]).strip()
            if val and val.replace(',', '').replace('.', '').isdigit():
                START_COL = col_idx
                break

        # Dò số ngày hiện có
        num_days = 0
        for col_idx in range(len(vals[8]) - 1, START_COL - 1, -1):
            val = str(vals[8][col_idx]).strip()
            if val and "IF(" not in val and "#" not in val and val != "":
                num_days = col_idx - START_COL + 1
                break

        if num_days <= 0: num_days = 1
        cols_to_scan = [START_COL + i for i in range(num_days)]

        # HÀM BÓC TÁCH DỮ LIỆU ĐA NĂNG CHO TỪNG HUB
        def extract_hub_data(vol_idx, wgt_idx, ms_idx, ms_rt_idx, fte_idx, bl_idx, chuyen_idxs, tre_idxs, lh_rt_idx):
            data = {
                "Ngày": [str(i+1) for i in range(num_days)],
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

        # LẤY CHỈ SỐ HCM HUB (Index = Dòng - 1)
        # Vol: Dòng 14(13), Wgt: 15(14), Missort: 20(19), %Ms: 21(20), FTE: 28(27), Backlog: 36(35), Tổng xe: 46-47(45-46), Xe trễ: 48-49(47-48), %LH: 52(51)
        df_hcm = extract_hub_data(13, 14, 19, 20, 27, 35, [45, 46], [47, 48], 51)

        # LẤY CHỈ SỐ BN HUB (Index = Dòng - 1)
        # Vol: Dòng 22(21), Wgt: 23(22), Missort: 24(23), %Ms: 25(24), FTE: 32(31), Backlog: 39(38), Tổng xe: 57-58(56-57), Xe trễ: 59-60(58-59), %LH: 63(62)
        df_bn = extract_hub_data(21, 22, 23, 24, 31, 38, [56, 57], [58, 59], 62)
        
        return df_hcm, df_bn
        
    except Exception as e:
        st.error(f"❌ Lỗi hệ thống: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# 3. GIAO DIỆN HIỂN THỊ CHUNG
st.markdown("<h1 style='text-align: center; color: #1E293B;'>J&T CARGO - KPI PERFORMANCE</h1>", unsafe_allow_html=True)
df_hcm, df_bn = get_data()

if df_hcm.empty and df_bn.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu.")
    st.stop()

# TẠO 2 TABS ĐỂ TÁCH BIỆT GIAO DIỆN
tab1, tab2 = st.tabs(["🏢 HCM HUB", "🏢 BN HUB"])

def render_dashboard(df, title_color):
    if df.empty:
        st.info("Chưa có dữ liệu cho Hub này.")
        return

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

    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<h5 style='color:{title_color};'>📦 Sản lượng & Chất lượng</h5>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng hàng", f"{int(total_vol):,}".replace(",", "."))
            m2.metric("Tổng Missort", f"{int(total_missort):,}")
            m3.metric("Tỷ lệ Missort", f"{final_missort_rate:.2f}%")
        with c2:
            st.markdown(f"<h5 style='color:{title_color};'>⚙️ Hiệu suất Tháng</h5>", unsafe_allow_html=True)
            m4, m5 = st.columns(2)
            m4.metric("HS Sản lượng", f"{header_pcs_month:.0f} Pcs/Tháng")
            m5.metric("HS Trọng lượng", f"{header_kg_month:,.0f} Kg/Tháng".replace(",", "."))
        with c3:
            st.markdown(f"<h5 style='color:{title_color};'>🚚 Vận tải & Tồn kho</h5>", unsafe_allow_html=True)
            m6, m7 = st.columns(2)
            m6.metric("Tổng Backlog", f"{int(total_backlog)} kiện")
            m7.metric("LH Ontime", f"{final_ontime_rate:.2f}%")

    st.markdown("---")

    st.subheader("Phân tích chi tiết Missort")
    fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Số đơn Missort'], name="Số đơn", marker_color='#94A3B8', width=0.4, 
                            text=[f"{v:g}" if pd.notna(v) else "" for v in df['Số đơn Missort']], textposition='outside'), secondary_y=False)
    fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers+text', 
                                text=[f"{v:g}%" if pd.notna(v) else "" for v in df['Tỷ lệ Missort (%)']], textposition='top right', line=dict(color='#4F46E5', width=3)), secondary_y=True)
    fig_ms.update_layout(xaxis_type='category', height=400, margin=dict(t=50, b=0), plot_bgcolor='white')
    st.plotly_chart(fig_ms, use_container_width=True)

    c_v1, c_v2 = st.columns(2)
    with c_v1:
        st.markdown("**Tổng lượng hàng xử lý**")
        fig_vol = px.bar(df, x="Ngày", y="Tổng lượng hàng", color_discrete_sequence=['#6366F1'])
        fig_vol.update_traces(text=[f"{v:g}" if pd.notna(v) else "" for v in df['Tổng lượng hàng']], textposition="outside")
        fig_vol.update_layout(xaxis_type='category', height=350, plot_bgcolor='white')
        st.plotly_chart(fig_vol, use_container_width=True)
    with c_v2:
        st.markdown("**Backlog tồn đọng hàng ngày**")
        fig_bl = px.bar(df, x="Ngày", y="Backlog tồn đọng", color_discrete_sequence=['#F43F5E'])
        fig_bl.update_traces(text=[f"{v:g}" if pd.notna(v) else "" for v in df['Backlog tồn đọng']], textposition="outside")
        fig_bl.update_layout(xaxis_type='category', height=350, plot_bgcolor='white')
        st.plotly_chart(fig_bl, use_container_width=True)

    c_t1, c_t2 = st.columns(2)
    with c_t1:
        st.markdown("**Đúng giờ Linehaul (%)**")
        fig_lh = px.line(df, x="Ngày", y="Tỷ lệ Linehaul đúng giờ (%)", markers=True, color_discrete_sequence=['#0EA5E9'])
        fig_lh.update_traces(text=[f"{v:g}%" if pd.notna(v) else "" for v in df['Tỷ lệ Linehaul đúng giờ (%)']], textposition="top center", mode="lines+markers+text")
        fig_lh.update_layout(xaxis_type='category', height=350, plot_bgcolor='white')
        st.plotly_chart(fig_lh, use_container_width=True)
    with c_t2:
        st.markdown("**Kiểm soát Chuyến xe (Đúng/Sai COT)**")
        fig_xe = px.bar(df, x="Ngày", y=["Xe Đúng COT (Tổng)", "Xe Sai COT (Tổng)"], color_discrete_map={"Xe Đúng COT (Tổng)": "#10B981", "Xe Sai COT (Tổng)": "#FB7185"})
        for trace in fig_xe.data:
            trace.text = [f"{v:g}" if pd.notna(v) else "" for v in trace.y]
            trace.textposition = "outside"
        fig_xe.update_layout(xaxis_type='category', barmode='group', height=350, plot_bgcolor='white', legend_title=None)
        st.plotly_chart(fig_xe, use_container_width=True)

    with st.expander("Bảng đối soát dữ liệu thô"):
        df_show = df.set_index("Ngày").T
        df_show = df_show.fillna("")
        st.dataframe(df_show, use_container_width=True)

# 4. GỌI HÀM VẼ GIAO DIỆN CHO TỪNG TAB
with tab1:
    render_dashboard(df_hcm, title_color="#0284C7") # Màu xanh cho HCM
with tab2:
    render_dashboard(df_bn, title_color="#059669")  # Màu xanh lá cho BN
