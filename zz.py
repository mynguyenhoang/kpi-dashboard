import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# --- CẤU HÌNH FEISHU ---
APP_ID = "cli_a9456e412bb89bce"
APP_SECRET = "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"
SPREADSHEET_TOKEN = "NIBWsB2ybhcsamtpF3wcbdL0nVb"
SHEET_ID = "OGehC6"  # Sheet name hoặc GID của bạn

# Hàm lấy Tenant Access Token
def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    r = requests.post(url, json=payload)
    return r.json().get("tenant_access_token")

# Hàm lấy dữ liệu từ Feishu Sheet
@st.cache_data(ttl=300) # Lưu bộ nhớ đệm 5 phút để tránh gọi API quá nhiều
def get_data_from_feishu():
    token = get_tenant_access_token()
    # Range lấy từ cột A đến AK (theo dashboard của bạn)
    # Lưu ý: Cần kiểm tra xem dữ liệu của bạn nằm ở dòng nào (Ví dụ A1:AK100)
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{SPREADSHEET_TOKEN}/values/{SHEET_ID}!A1:AK100"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    res_data = response.json()
    
    if res_data.get("code") != 0:
        st.error(f"Lỗi lấy dữ liệu Feishu: {res_data.get('msg')}")
        return pd.DataFrame()

    values = res_data['data']['valueRange']['values']
    
    # Chuyển đổi list of lists thành DataFrame
    # Lưu ý Quan Trọng: Vì cấu trúc Sheet của bạn có header phức tạp, 
    # bạn cần chọn đúng hàng chứa dữ liệu.
    raw_df = pd.DataFrame(values)
    
    # XỬ LÝ DỮ LIỆU CỤ THỂ THEO FILE CỦA BẠN:
    # Bạn cần map lại các dòng dựa trên hình ảnh dashboard:
    # Ví dụ: Dòng 5 là Tổng lượng hàng, Dòng 6 là Missort...
    
    data_cleaned = {
        "Ngày": [str(i) for i in range(1, 16)],
        "Tổng lượng hàng": raw_df.iloc[4, 2:17].fillna(0).astype(int).tolist(), # Dòng 5 (index 4), từ cột C (index 2)
        "Số đơn Missort": raw_df.iloc[5, 2:17].fillna(0).astype(int).tolist(),
        "Tỷ lệ Missort (%)": raw_df.iloc[6, 2:17].str.replace('%','').fillna(0).astype(float).tolist(),
        "Tổng nhân sự": raw_df.iloc[9, 2:17].fillna(0).astype(float).tolist(),
        "Tổng trọng lượng (Kg)": raw_df.iloc[10, 2:17].fillna(0).astype(float).tolist(),
        "Tỷ lệ Linehaul đúng giờ (%)": raw_df.iloc[26, 2:17].str.replace('%','').fillna(0).astype(float).tolist(),
        "Backlog tồn đọng": raw_df.iloc[14, 2:17].fillna(0).astype(int).tolist(),
        "Xe Đúng COT (Tổng)": raw_df.iloc[19, 2:17].fillna(0).astype(int).tolist(),
        "Xe Sai COT (Tổng)": raw_df.iloc[22, 2:17].fillna(0).astype(int).tolist()
    }
    
    return pd.DataFrame(data_cleaned)

# --- THAY ĐỔI DÒNG NÀY TRONG CODE CŨ CỦA BẠN ---
try:
    df = get_data_from_feishu()
except Exception as e:
    st.error(f"Không thể kết nối dữ liệu: {e}")
    st.stop()
