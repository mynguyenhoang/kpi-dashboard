import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

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
        st.error("❌ Không lấy được Token Feishu. Hãy kiểm tra lại APP_ID/SECRET.")
        return pd.DataFrame(), pd.DataFrame()

    # Quét rộng tới dòng 80 để bao trọn Linehaul
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        if res.get("code") != 0:
            st.error(f"❌ Lỗi Feishu: {res.get('msg')}")
            return pd.DataFrame(), pd.DataFrame()

        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
        if not vals or len(vals) < 60:
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

        # --- LOGIC TÌM NGÀY ĐÃ ĐƯỢC FIX ---
        # Tìm chính xác dòng nào đang chứa chữ "1", "2", "3"... (Trong ảnh là Dòng 4)
        date_row_idx = -1
        start_col_idx = -1
        
        for r in range(min(10, len(vals))):
            for c in range(len(vals[r])):
                val = str(vals[r][c]).strip()
                if val == "1" and c > 2: # Số 1 bắt đầu sau cột Tổng (thường là cột G)
                    date_row_idx = r
                    start_col_idx = c
                    break
            if date_row_idx != -1: break

        num_days = 1
        if date_row_idx != -1:
            max_day = 1
            for c in range(start_col_idx, len(vals[date_row_idx])):
                val = str(vals[date_row_idx][c]).strip()
                if val.isdigit():
                    max_day = max(max_day, int(val))
            num_days = max_day
            cols_to_scan = [start_col_idx + i for i in range(num_days)]
        else:
            cols_to_scan = [6 + i for i in range(26)] # Dự phòng mặc định bắt đầu từ cột G, 26 ngày
            num_days = 26

        def extract_hub_data(vol_idx, wgt_idx, ms_idx, ms_rt_idx, fte_idx, bl_idx, chuyen_idxs, tre_idxs, lh_rt_idx):
            data = {
                "Ngày": [f"Ngày {i+1}" for i in range(num_days)],
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

        # MAP CHÍNH XÁC THEO ROW TRÊN EXCEL (Index trong code = Row trên Excel trừ đi 1)
        # 1. HCM HUB
        df_hcm = extract_hub_data(
            vol_idx=8,        # Dòng 9: HCM Tổng lượng hàng xử lý
            wgt_idx=9,        # Dòng 10: HCM Tổng trọng lượng xử lý
            ms_idx=18,        # Dòng 19: HCM Tổng số đơn Missort
            ms_rt_idx=19,     # Dòng 20: HCM Tỷ lệ Missort
            fte_idx=25,       # Dòng 26: HCM Tổng hệ số FTE
            bl_idx=35,        # Dòng 36: HCM Tổng đơn tồn đọng (Backlog)
            chuyen_idxs=[44, 45], # Dòng 45, 46: Tổng chuyến Shuttle & Linehaul
            tre_idxs=[46, 47],    # Dòng 47, 48: Tổng trễ Shuttle & Linehaul
            lh_rt_idx=49      # Dòng 50: % LH Depart OntimeLinehaul
        )

        # 2. BN HUB
        df_bn = extract_hub_data(
            vol_idx=14,       # Dòng 15: BN Tổng lượng hàng xử lý
            wgt_idx=15,       # Dòng 16: BN Tổng trọng lượng xử lý
            ms_idx=21,        # Dòng 22: BN Tổng số đơn Missort
            ms_rt_idx=22,     # Dòng 23: BN Tỷ lệ Missort
            fte_idx=31,       # Dòng 32: BN Tổng hệ số FTE
            bl_idx=36,        # Dòng 37: BN Tổng đơn tồn đọng (Backlog)
            chuyen_idxs=[53, 54], # Dòng 54, 55: BN Tổng chuyến Shuttle & Linehaul
            tre_idxs=[55, 56],    # Dòng 56, 57: BN Tổng trễ Shuttle & Linehaul
            lh_rt_idx=58      # Dòng 59: BN % LH Depart OntimeLinehaul
        )
        
        return df_hcm, df_bn
        
    except Exception as e:
        st.error(f"❌ Lỗi hệ thống: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# 3. GIAO DIỆN HIỂN THỊ CHUNG
st.markdown("<h1 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>📊 J&T CARGO KPI DASHBOARD</h1>", unsafe_allow_html=True)
df_hcm, df_bn = get_data()

if df_hcm.empty and df_bn.empty:
    st.warning("⚠️ Không tìm thấy dữ liệu. Vui lòng kiểm tra lại cấu trúc file Feishu.")
    st.stop()

tab1, tab2 = st.tabs(["🏢 HỒ CHÍ MINH HUB", "🏢 BẮC NINH HUB"])

def render_dashboard(df, primary_color):
    if df.empty:
        st.info("Chưa có dữ liệu cho Hub này.")
        return

    # TÍNH TOÁN HEADER METRICS CHỈ LẤY CÁC NGÀY CÓ SỐ LIỆU THỰC
    valid_vol = df['Tổng lượng hàng'].dropna()
    total_vol = valid_vol.sum() 
    total_weight = df['Tổng trọng lượng (Kg)'].dropna().sum()
    total_missort = df['Số đơn Missort'].dropna().sum()
    total_backlog = df['Backlog tồn đọng'].dropna().sum()
    total_man_days = df['Tổng nhân sự'].dropna().sum()

    working_days = 26 
    header_pcs_month = (total_vol / total_man_days * working_days) if total_man_days > 0 else 0
    header_kg_month = (total_weight / total_man_days * working_days) if total_man_days > 0 else 0

    total_xe_dung = df['Xe Đúng COT (Tổng)'].dropna().sum()
    total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].dropna().sum()
    final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0
    final_missort_rate = (total_missort / total_vol * 100) if total_vol > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Tổng Sản Lượng", f"{int(total_vol):,}".replace(",", "."))
    c2.metric("⚖️ Tổng Trọng Lượng", f"{int(total_weight):,}".replace(",", ".") + " kg")
    c3.metric("❌ Tổng Missort", f"{int(total_missort):,}", f"{final_missort_rate:.2f}% tỷ lệ")
    c4.metric("📦 Tổng Backlog", f"{int(total_backlog):,}")
    c5.metric("🚚 Tỷ Lệ LH Đúng Giờ", f"{final_ontime_rate:.2f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"<h4 style='color: {primary_color};'>1. Đánh giá Sản Lượng & Chất Lượng Phân Loại (Missort)</h4>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_vol = px.area(df, x="Ngày", y="Tổng lượng hàng", title="Biểu đồ Sản lượng hàng ngày")
        fig_vol.update_traces(line_color=primary_color, fillcolor='rgba(56, 189, 248, 0.2)', mode='lines+markers+text', 
                              text=[f"{v:g}" if pd.notna(v) else "" for v in df['Tổng lượng hàng']], textposition="top center")
        fig_vol.update_layout(plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10))
        fig_vol.update_xaxes(showgrid=False)
        fig_vol.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_chart2:
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Số đơn Missort'], name="Số đơn Missort", marker_color='#94a3b8', opacity=0.7), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
        fig_ms.update_layout(title_text="Phân tích Missort (Số lượng & Tỷ lệ)", plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_ms.update_xaxes(showgrid=False)
        fig_ms.update_yaxes(showgrid=True, gridcolor='#f1f5f9', secondary_y=False)
        st.plotly_chart(fig_ms, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải (Linehaul) & Hàng Tồn (Backlog)</h4>", unsafe_allow_html=True)
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        fig_xe = go.Figure()
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['Xe Đúng COT (Tổng)'], name="Đúng giờ COT", marker_color='#10b981'))
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['Xe Sai COT (Tổng)'], name="Trễ giờ COT", marker_color='#f43f5e'))
        fig_xe.update_layout(title="Kiểm soát Chuyến xe chạy COT", barmode='stack', plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_xe.update_xaxes(showgrid=False)
        fig_xe.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_xe, use_container_width=True)

    with col_chart4:
        fig_bl = px.bar(df, x="Ngày", y="Backlog tồn đọng", title="Backlog tồn đọng cuối ngày")
        fig_bl.update_traces(marker_color='#f59e0b', text=[f"{v:g}" if pd.notna(v) else "" for v in df['Backlog tồn đọng']], textposition="outside")
        fig_bl.update_layout(plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10))
        fig_bl.update_xaxes(showgrid=False)
        fig_bl.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_bl, use_container_width=True)

    with st.expander("🔍 Bảng đối soát dữ liệu thô"):
        df_show = df.set_index("Ngày").T
        df_show = df_show.fillna("")
        st.dataframe(df_show, use_container_width=True)

with tab1:
    render_dashboard(df_hcm, primary_color="#0ea5e9") 
with tab2:
    render_dashboard(df_bn, primary_color="#059669")
