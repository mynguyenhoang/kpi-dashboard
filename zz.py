import requests
import re # Thêm thư viện này ở đầu file

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
    r = requests.post(url, json=payload)
    return r.json().get("tenant_access_token")

@st.cache_data(ttl=300)
def get_data():
    token = get_tenant_access_token()
    # Sử dụng API đọc giá trị hiển thị (v2)
    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!C5:AQ30?valueRenderOption=ToString"
    headers = {"Authorization": f"Bearer {token}"}
    
    res = requests.get(url, headers=headers).json()
    if res.get("code") != 0:
        st.error(f"Lỗi Feishu: {res.get('msg')}")
        return pd.DataFrame()

    vals = res['data']['valueRange']['values']

    # Hàm xử lý rác: Nếu là công thức hoặc chữ thì trả về 0, nếu là số thì lấy số
    def clean_val(v):
        if not v or str(v).startswith('=') or str(v).startswith('IF('):
            return 0
        # Xóa dấu % và dấu phẩy nếu có
        clean_s = str(v).replace('%', '').replace(',', '').strip()
        try:
            return float(clean_s)
        except:
            return 0

    data = {
        "Ngày": [str(i) for i in range(1, 16)],
        "Tổng lượng hàng": [clean_val(v) for v in vals[0][:15]],     # Dòng 5
        "Số đơn Missort": [clean_val(v) for v in vals[1][:15]],      # Dòng 6
        "Tỷ lệ Missort (%)": [clean_val(v) for v in vals[2][:15]],   # Dòng 7
        "Tổng nhân sự": [clean_val(v) for v in vals[5][:15]],        # Dòng 10
        "Tổng trọng lượng (Kg)": [clean_val(v) for v in vals[6][:15]],   # Dòng 11
        "Backlog tồn đọng": [clean_val(v) for v in vals[10][:15]],     # Dòng 15
        "Xe Đúng COT (Tổng)": [clean_val(v) for v in vals[15][:15]],   # Dòng 20
        "Xe Sai COT (Tổng)": [clean_val(v) for v in vals[18][:15]],    # Dòng 23
        "Tỷ lệ Linehaul đúng giờ (%)": [clean_val(v) for v in vals[22][:15]], # Dòng 27
    }
    return pd.DataFrame(data)
