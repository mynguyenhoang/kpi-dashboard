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
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": "cli_a9456e412bb89bce", 
        "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"
    }
    r = requests.post(url, json=payload)
    return r.json().get("tenant_access_token")

@st.cache_data(ttl=300)
def get_data():
    token = get_tenant_access_token()
    # Thêm ?valueRenderOption=ToString để lấy giá trị đã tính toán, không lấy công thức
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!C5:AQ30?valueRenderOption=ToString"
    headers = {"Authorization": f"Bearer {token}"}
    
    res = requests.get(url, headers=headers).json()
    if res.get("code") != 0:
        st.error(f"Lỗi Feishu: {res.get('msg')}")
        return pd.DataFrame()

    vals = res['data']['valueRange']['values']

    # Hàm xử lý để tránh lỗi khi gặp ô trống hoặc ký tự lạ
    def clean_val(v):
        if v is None or str(v).strip() == "" or str(v).startswith('IF(') or str(v).startswith('='):
            return 0
        try:
            # Xóa dấu %, dấu phẩy, khoảng trắng
            s = str(v).replace('%', '').replace(',', '').strip()
            return float(s)
        except:
            return 0

    data = {
        "Ngày": [str(i) for i in range(1, 16)],
        "Tổng lượng hàng": [clean_val(vals[0][i]) if i < len(vals[0]) else 0 for i in range(15)],
        "Số đơn Missort": [clean_val(vals[1][i]) if i < len(vals[1]) else 0 for i in range(15)],
        "Tỷ lệ Missort (%)": [clean_val(vals[2][i]) if i < len(vals[2]) else 0 for i in range(15)],
        "Tổng nhân sự": [clean_val(vals[5][i]) if i < len(vals[5]) else 0 for i in range(15)],
        "Tổng trọng lượng (Kg)": [clean_val(vals[6][i]) if i < len(vals[6]) else 0 for i in range(15)],
        "Backlog tồn đọng": [clean_val(vals[10][i]) if i < len(vals[10]) else 0 for i in range(15)],
        "Xe Đúng COT (Tổng)": [clean_val(vals[15][i]) if i < len(vals[15]) else 0 for i in range(15)],
        "Xe Sai COT (Tổng)": [clean_val(vals[18][i]) if i < len(vals[18]) else 0 for i in range(15)],
        "Tỷ lệ Linehaul đúng giờ (%)": [clean_val(vals[22][i]) if i < len(vals[22]) else 0 for i in range(15)],
    }
    return pd.DataFrame(data)

# Gọi dữ liệu
try:
    df = get_data()
except Exception as e:
    st.error(f"Lỗi xử lý dữ liệu: {e}")
    st.stop()

# --- TỪ ĐÂY TRỞ XUỐNG GIỮ NGUYÊN CODE GIAO DIỆN CŨ CỦA BẠN ---
# (Phần 3. LOGIC TÍNH TOÁN KPI và 4. GIAO DIỆN)
