import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo HCM - KPI Dashboard Full", layout="wide")

# 2. HÀM LẤY DỮ LIỆU TỰ ĐỘNG TỪ FEISHU
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
        st.error("❌ Không lấy được Token. Kiểm tra lại APP_ID/SECRET hoặc kết nối mạng.")
        return pd.DataFrame()

    # Lấy từ C1 để mapping Index cho dễ (Index = Dòng Excel - 1)
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!C1:AQ40?valueRenderOption=ToString"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("code") != 0:
            st.error(f"❌ Lỗi Feishu: {res.get('msg')} - (Khả năng cao Bot chưa được Add vào Sheet)")
            return pd.DataFrame()

        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
        if not vals:
            return pd.DataFrame()

        # Hàm làm sạch dữ liệu
        def clean_val(row_idx, col_idx):
            try:
                if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                    v = vals[row_idx][col_idx]
                    if not v or "IF(" in str(v) or str(v).startswith("="): 
                        return 0
                    # Ép kiểu an toàn
                    return float(str(v).replace('%', '').replace(',', '').strip())
                return 0
            except: return 0

        # MAPPING TỌA ĐỘ (Dựa trên ảnh: Index = Số dòng Excel trừ đi 1)
        # Cột dữ liệu ngày 1-15 tương ứng col_idx từ 0 đến 14
        data = {
            "Ngày": [str(i) for i in range(1, 16)],
            "Tổng lượng hàng": [clean_val(4, i) for i in range(15)],       # Dòng 5 -> Index 4
            "Số đơn Missort": [clean_val(5, i) for i in range(15)],        # Dòng 6 -> Index 5
            "Tỷ lệ Missort (%)": [clean_val(6, i) for i in range(15)],     # Dòng 7 -> Index 6
            "Tổng nhân sự": [clean_val(9, i) for i in range(15)],          # Dòng 10 -> Index 9
            "Tổng trọng lượng (Kg)": [clean_val(10, i) for i in range(15)],# Dòng 11 -> Index 10
            "Backlog tồn đọng": [clean_val(15, i) for i in range(15)],     # Dòng 16 -> Index 15
            "Xe Đúng COT (Tổng)": [clean_val(20, i) for i in range(15)],   # Dòng 21 -> Index 20
            "Xe Sai COT (Tổng)": [clean_val(23, i) for i in range(15)],    # Dòng 24 -> Index 23
            "Tỷ lệ Linehaul đúng giờ (%)": [clean_val(27, i) for i in range(15)] # Dòng 28 -> Index 27
        }
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ Lỗi hệ thống: {str(e)}")
        return pd.DataFrame()

# 3. LẤY & KIỂM TRA DỮ LIỆU
df = get_data()

if df.empty:
    st.warning("⚠️ Đang chờ dữ liệu từ Feishu... Nếu mãi không lên, hãy kiểm tra lại nút 'Add App' trên Sheet.")
    st.stop()

# 4. LOGIC TÍNH TOÁN KPI (Có bảo vệ chống lỗi chia 0)
total_vol = df['Tổng lượng hàng'].sum() 
total_weight = df['Tổng trọng lượng (Kg)'].sum()
total_missort = df['Số đơn Missort'].sum()
total_backlog = df['Backlog tồn đọng'].sum()
total_man_days = df['Tổng nhân sự'].sum()

working_days = 26 
header_pcs_month = (total_vol / total_man_days) * working_days if total_man_days > 0 else 0
header_kg_month = (total_weight / total_man_days) * working_days if total_man_days > 0 else 0

total_xe_dung = df['Xe Đúng COT (Tổng)'].sum()
total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum()
final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0
final_missort_rate = (total_missort / total_vol * 100) if total_vol > 0 else 0

# 5. GIAO DIỆN HIỂN THỊ
st.markdown("<h1 style='text-align: center; color: #1E293B;'>J&T CARGO HCM - KPI PERFORMANCE</h1>", unsafe_allow_html=True)

# THẺ CHỈ SỐ HEADER
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### 📦 Sản lượng & Chất lượng")
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng hàng", f"{int(total_vol):,}".replace(",", "."))
        m2.metric("Tổng Missort", f"{int(total_missort):,}")
        m3.metric("Tỷ lệ Missort", f"{final_missort_rate:.1f}%")
    with c2:
        st.markdown("##### ⚡ Hiệu suất Tháng (26 Công)")
        m4, m5 = st.columns(2)
        m4.metric("HS Sản lượng", f"{header_pcs_month:.0f} Pcs/Tháng")
        m5.metric("HS Trọng lượng", f"{header_kg_month:,.0f} Kg/Tháng".replace(",", "."))
    with c3:
        st.markdown("##### 🚚 Vận tải & Tồn kho")
        m6, m7 = st.columns(2)
        m6.metric("Tổng Backlog", f"{int(total_backlog)} kiện")
        m7.metric("LH Ontime", f"{final_ontime_rate:.1f}%")

st.markdown("---")

# HÀNG 1: BIỂU ĐỒ MISSORT
st.subheader("Phân tích chi tiết Missort")
fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Số đơn Missort'], name="Số đơn", marker_color='#94A3B8', width=0.4, text=df['Số đơn Missort'], textposition='outside'), secondary_y=False)
fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers+text', text=[f"{val}%" for val in df['Tỷ lệ Missort (%)']], textposition='top right', line=dict(color='#4F46E5', width=3)), secondary_y=True)
fig_ms.update_layout(xaxis_type='category', height=400, margin=dict(t=50, b=0), plot_bgcolor='white')
st.plotly_chart(fig_ms, use_container_width=True)

# HÀNG 2: VOL & BACKLOG
c_v1, c_v2 = st.columns(2)
with c_v1:
    st.markdown("**Tổng lượng hàng xử lý (Số đơn thực tế)**")
    fig_vol = px.bar(df, x="Ngày", y="Tổng lượng hàng", text="Tổng lượng hàng", color_discrete_sequence=['#6366F1'])
    fig_vol.update_traces(textposition="outside")
    fig_vol.update_layout(xaxis_type='category', height=350, plot_bgcolor='white')
    st.plotly_chart(fig_vol, use_container_width=True)
with c_v2:
    st.markdown("**Backlog tồn đọng hàng ngày**")
    fig_bl = px.bar(df, x="Ngày", y="Backlog tồn đọng", text="Backlog tồn đọng", color_discrete_sequence=['#F43F5E'])
    fig_bl.update_traces(textposition="outside")
    fig_bl.update_layout(xaxis_type='category', height=350, plot_bgcolor='white')
    st.plotly_chart(fig_bl, use_container_width=True)

# HÀNG 3: LINEHAUL & COT
c_t1, c_t2 = st.columns(2)
with c_t1:
    st.markdown("**Đúng giờ Linehaul (%)**")
    fig_lh = px.line(df, x="Ngày", y="Tỷ lệ Linehaul đúng giờ (%)", markers=True, color_discrete_sequence=['#0EA5E9'])
    fig_lh.update_traces(text=[f"{v}%" for v in df['Tỷ lệ Linehaul đúng giờ (%)']], textposition="top center", mode="lines+markers+text")
    fig_lh.update_layout(xaxis_type='category', height=350, plot_bgcolor='white')
    st.plotly_chart(fig_lh, use_container_width=True)
with c_t2:
    st.markdown("**Kiểm soát Chuyến xe (Đúng/Sai COT)**")
    fig_xe = px.bar(df, x="Ngày", y=["Xe Đúng COT (Tổng)", "Xe Sai COT (Tổng)"], text_auto=True, color_discrete_map={"Xe Đúng COT (Tổng)": "#10B981", "Xe Sai COT (Tổng)": "#FB7185"})
    fig_xe.update_layout(xaxis_type='category', barmode='group', height=350, plot_bgcolor='white', legend_title=None)
    st.plotly_chart(fig_xe, use_container_width=True)

# BẢNG DỮ LIỆU THÔ
with st.expander("Bảng đối soát dữ liệu (Dữ liệu kéo từ Feishu)"):
    st.dataframe(df.set_index("Ngày").T, use_container_width=True)
