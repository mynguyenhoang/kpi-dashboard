import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo - Diagnostic Dashboard", layout="wide")

# 2. HÀM LẤY DỮ LIỆU (CÓ CHẾ ĐỘ SOI LỖI)
def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
    r = requests.post(url, json=payload)
    return r.json().get("tenant_access_token")

@st.cache_data(ttl=10) # Set 10s để update data liên tục khi test
def get_diagnostic_data():
    token = get_tenant_access_token()
    # Vùng lấy dữ liệu rộng hơn để bao quát (Dòng 1 đến 40)
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!C1:AQ40?valueRenderOption=ToString"
    headers = {"Authorization": f"Bearer {token}"}
    
    res = requests.get(url, headers=headers).json()
    return res

# --- GIAO DIỆN KIỂM TRA ---
st.title("🔍 HỆ THỐNG CHẨN ĐOÁN DỮ LIỆU")

res = get_diagnostic_data()

# HIỂN THỊ TRẠNG THÁI KẾT NỐI
if res.get("code") == 0:
    st.success("✅ Kết nối Feishu THÀNH CÔNG!")
    vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    
    with st.expander("👀 NHẤN VÀO ĐÂY ĐỂ SOI DỮ LIỆU THÔ (Debug)"):
        if not vals:
            st.warning("⚠️ Cảnh báo: Kết nối được nhưng mảng dữ liệu trả về bị RỖNG [ ].")
        else:
            st.write("Dưới đây là những gì con Bot đang nhìn thấy trên Sheet của ông:")
            st.table(vals[:15]) # Hiển thị 15 dòng đầu tiên để check tọa độ
else:
    st.error(f"❌ Lỗi kết nối: {res.get('msg')}")
    st.write(res)
    st.stop()

# --- LOGIC XỬ LÝ DATA (Nếu có dữ liệu) ---
if vals:
    def clean_val(r, c):
        try:
            if r < len(vals) and c < len(vals[r]):
                v = str(vals[r][c]).replace('%', '').replace(',', '').strip()
                if not v or "IF(" in v or v == "None": return 0
                return float(v)
            return 0
        except: return 0

    # Mapping lại tọa độ dựa trên dữ liệu thô vừa soi được
    # Lưu ý: Index trong code = Số dòng trên Excel - 1
    df = pd.DataFrame({
        "Ngày": [str(i) for i in range(1, 16)],
        "Tổng lượng hàng": [clean_val(4, i) for i in range(15)],       # Dòng 5
        "Số đơn Missort": [clean_val(5, i) for i in range(15)],        # Dòng 6
        "Tỷ lệ Missort (%)": [clean_val(6, i) for i in range(15)],     # Dòng 7
        "Tổng nhân sự": [clean_val(9, i) for i in range(15)],          # Dòng 10
        "Tổng trọng lượng (Kg)": [clean_val(10, i) for i in range(15)],# Dòng 11
        "Backlog tồn đọng": [clean_val(15, i) for i in range(15)],     # Dòng 16
        "Xe Đúng COT (Tổng)": [clean_val(20, i) for i in range(15)],   # Dòng 21
        "Xe Sai COT (Tổng)": [clean_val(23, i) for i in range(15)],    # Dòng 24
        "Tỷ lệ Linehaul đúng giờ (%)": [clean_val(27, i) for i in range(15)] # Dòng 28
    })

    # --- TỚI ĐÂY LÀ PHẦN VẼ BIỂU ĐỒ CŨ CỦA ÔNG ---
    total_vol = df['Tổng lượng hàng'].sum()
    # ... (Copy tiếp phần vẽ Chart của ông vào đây)
    st.divider()
    st.subheader("Kết quả Dashboard thực tế:")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng hàng thực tế", f"{total_vol:,.0f}")
    # ...
