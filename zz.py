import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo HCM - KPI Dashboard Full", layout="wide")

# 2. DỮ LIỆU ĐÚNG TỪ EXCEL (FULL FIELDS)
def get_data():
    days = [str(i) for i in range(1, 16)]
    data = {
        "Ngày": days,
        "Tổng lượng hàng": [3442, 3325, 2247, 3081, 1765, 2640, 2122, 3563, 2831, 4308, 3276, 1513, 6372, 3936, 2745],
        "Số đơn Missort": [24, 24, 14, 23, 3, 63, 17, 12, 35, 21, 35, 27, 29, 142, 656],
        "Tỷ lệ Missort (%)": [1, 1, 1, 1, 0, 2, 1, 0, 1, 0, 1, 2, 0, 4, 24],
        "Tổng nhân sự": [29.75, 46.25, 43.75, 0, 31.25, 47.5, 47.5, 38.75, 40, 44, 0, 40.25, 46.25, 45.25, 42.5],
        "Tổng trọng lượng (Kg)": [78787, 76763, 54303, 77678, 42797, 63041, 51347, 79889, 70240, 95540, 74467, 37364, 133332, 100013, 62429],
        "Tỷ lệ Linehaul đúng giờ (%)": [77, 79, 76, 71, 76, 83, 76, 72, 75, 72, 77, 71, 66, 82, 75],
        "Backlog tồn đọng": [3, 3, 0, 0, 5, 0, 0, 1, 1, 0, 0, 0, 1, 1, 46],
        "Xe Đúng COT (Tổng)": [13, 25, 21, 19, 25, 36, 25, 26, 31, 22, 3, 21, 22, 24, 29],
        "Xe Sai COT (Tổng)": [4, 4, 8, 10, 3, 6, 3, 7, 8, 9, 2, 8, 12, 8, 7]
    }
    return pd.DataFrame(data)

df = get_data()

# 3. LOGIC TÍNH TOÁN KPI CHUẨN DATA
total_vol = df['Tổng lượng hàng'].sum() 
total_weight = df['Tổng trọng lượng (Kg)'].sum()
total_missort = df['Số đơn Missort'].sum()
total_backlog = df['Backlog tồn đọng'].sum()
total_man_days = df['Tổng nhân sự'].sum()

# Hiệu suất 1 tháng (Dựa trên 26 ngày công chuẩn)
working_days = 26 
header_pcs_month = (total_vol / total_man_days) * working_days
header_kg_month = (total_weight / total_man_days) * working_days

# Tỷ lệ xe đúng giờ tổng kỳ
total_xe_dung = df['Xe Đúng COT (Tổng)'].sum()
total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum()
final_ontime_rate = (total_xe_dung / total_xe_chay) * 100
final_missort_rate = (total_missort / total_vol) * 100

# 4. GIAO DIỆN
st.markdown("<h1 style='text-align: center; color: #1E293B;'>J&T CARGO HCM - KPI PERFORMANCE</h1>", unsafe_allow_html=True)

# THẺ CHỈ SỐ HEADER
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### 📦 Sản lượng & Chất lượng")
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng hàng", f"{total_vol:,}".replace(",", "."))
        m2.metric("Tổng Missort", f"{total_missort:,}")
        m3.metric("Tỷ lệ Missort", f"{final_missort_rate:.1f}%")
    with c2:
        st.markdown("##### ⚡ Hiệu suất Tháng (26 Công)")
        m4, m5 = st.columns(2)
        m4.metric("HS Sản lượng", f"{header_pcs_month:.0f} Pcs/Tháng")
        m5.metric("HS Trọng lượng", f"{header_kg_month:,.0f} Kg/Tháng".replace(",", "."))
    with c3:
        st.markdown("##### 🚚 Vận tải & Tồn kho")
        m6, m7 = st.columns(2)
        m6.metric("Tổng Backlog", f"{total_backlog} kiện")
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
with st.expander("Bảng đối soát dữ liệu"):
    st.dataframe(df.set_index("Ngày").T, use_container_width=True)