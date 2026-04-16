import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo HCM - KPI Dashboard Full", layout="wide")

# 2. HÀM LẤY DỮ LIỆU
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except Exception as e:
        st.error(f"Lỗi lấy Token: {e}")
        return None

@st.cache_data(ttl=60) # Thử để 1 phút để test dữ liệu nhảy nhanh
def get_data():
    token = get_tenant_access_token()
    if not token: return pd.DataFrame()

    # Dùng API v2 với option ToString để lấy kết quả tính toán
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!C5:AQ30?valueRenderOption=ToString"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("code") != 0:
            st.error(f"Lỗi Feishu API: {res.get('msg')}")
            return pd.DataFrame()

        vals = res['data']['valueRange']['values']
        
        # Hàm làm sạch dữ liệu cực mạnh
        def clean_val(row_idx, col_idx):
            try:
                # Kiểm tra xem hàng và cột có tồn tại không
                if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                    v = vals[row_idx][col_idx]
                    if v is None or str(v).strip() == "" or "IF(" in str(v):
                        return 0
                    # Xóa % và dấu phẩy
                    s = str(v).replace('%', '').replace(',', '').strip()
                    return float(s)
                return 0
            except:
                return 0

        data = {
            "Ngày": [str(i) for i in range(1, 16)],
            "Tổng lượng hàng": [clean_val(0, i) for i in range(15)],
            "Số đơn Missort": [clean_val(1, i) for i in range(15)],
            "Tỷ lệ Missort (%)": [clean_val(2, i) for i in range(15)],
            "Tổng nhân sự": [clean_val(5, i) for i in range(15)],
            "Tổng trọng lượng (Kg)": [clean_val(6, i) for i in range(15)],
            "Backlog tồn đọng": [clean_val(10, i) for i in range(15)],
            "Xe Đúng COT (Tổng)": [clean_val(15, i) for i in range(15)],
            "Xe Sai COT (Tổng)": [clean_val(18, i) for i in range(15)],
            "Tỷ lệ Linehaul đúng giờ (%)": [clean_val(22, i) for i in range(15)],
        }
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
        return pd.DataFrame()

# 3. KIỂM TRA DỮ LIỆU TRƯỚC KHI VẼ
df = get_data()

if df.empty:
    st.warning("⚠️ Đang chờ dữ liệu từ Feishu... Hãy đảm bảo bạn đã 'Add App' vào Sheet và kiểm tra quyền truy cập.")
    st.stop() # Dừng app tại đây nếu không có dữ liệu để tránh lỗi trắng trang

# --- PHẦN LOGIC TÍNH TOÁN (Giữ nguyên của Mỹ) ---
total_vol = df['Tổng lượng hàng'].sum() 
total_weight = df['Tổng trọng lượng (Kg)'].sum()
total_missort = df['Số đơn Missort'].sum()
total_backlog = df['Backlog tồn đọng'].sum()
total_man_days = df['Tổng nhân sự'].sum()

# Tránh lỗi chia cho 0 nếu chưa có nhân sự
if total_man_days == 0: total_man_days = 1

working_days = 26 
header_pcs_month = (total_vol / total_man_days) * working_days
header_kg_month = (total_weight / total_man_days) * working_days

total_xe_dung = df['Xe Đúng COT (Tổng)'].sum()
total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum()
final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0
final_missort_rate = (total_missort / total_vol * 100) if total_vol > 0 else 0

# --- PHẦN GIAO DIỆN (Giữ nguyên của Mỹ) ---
st.markdown("<h1 style='text-align: center; color: #1E293B;'>J&T CARGO HCM - KPI PERFORMANCE</h1>", unsafe_allow_html=True)

# THẺ CHỈ SỐ HEADER (Copy phần code m1, m2... cũ của Mỹ vào đây)
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### 📦 Sản lượng & Chất lượng")
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng hàng", f"{total_vol:,}".replace(",", "."))
        m2.metric("Tổng Missort", f"{total_missort:,}")
        m3.metric("Tỷ lệ Missort", f"{final_missort_rate:.1f}%")
    # ... tương tự cho c2, c3 ...

st.markdown("---")
# (Chèn tiếp các phần biểu đồ fig_ms, fig_vol... cũ của bạn vào bên dưới)
