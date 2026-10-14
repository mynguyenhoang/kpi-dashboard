import streamlit as st
import requests

st.set_page_config(layout="wide")
st.write("### 🔍 CÔNG CỤ BẮT BỆNH DỮ LIỆU FEISHU")

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": "cli_a9456e412bb89bce", 
        "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"
    }
    return requests.post(url, json=payload).json().get("tenant_access_token")

token = get_tenant_access_token()
url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
headers = {"Authorization": f"Bearer {token}"}

res = requests.get(url, headers=headers).json()
vals = res.get('data', {}).get('valueRange', {}).get('values', [])

for i, row in enumerate(vals):
    if i < 68:
        continue
    text_preview = " | ".join([str(x)[:80] for x in row[:3] if x is not None])
    st.write(f"**Index {i}**: {text_preview}")
