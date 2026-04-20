import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.kpi-table {width: 100%;border-collapse: collapse;margin-bottom: 30px;background-color: white;}
.kpi-table th {background-color: #1f2937;color: white;padding: 10px;text-align: center;}
.kpi-table td {padding: 10px;border: 1px solid #d1d5db;}
.col-pillar {font-weight: bold;text-align: center;background-color: #f8fafc;}
.col-metric {font-weight: 600;}
.col-num {text-align: right;font-family: monospace;}
.col-mtd {text-align: right;font-weight: bold;background-color: #f0fdf4;}
</style>
""", unsafe_allow_html=True)

# ================= TOKEN =================
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

# ================= DATA =================
@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers).json()
    vals = res.get('data', {}).get('valueRange', {}).get('values', [])

    def clean_val(row_idx, col_idx):
        try:
            v = vals[row_idx][col_idx]
            str_v = str(v).strip()

            if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v:
                return np.nan

            s = str_v.replace('%', '').replace(',', '').strip()

            # ✅ FIX 1: KHÔNG convert '-' thành 0 nữa
            if s == '-': 
                return np.nan

            return float(s)
        except:
            return np.nan

    start_col_idx = 6
    num_days = 31
    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}

        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]

        lh_c_list = [clean_val(lhc_idx, c) for c in cols_to_scan]
        lh_t_list = [clean_val(lht_idx, c) for c in cols_to_scan]
        sh_c_list = [clean_val(shc_idx, c) for c in cols_to_scan]
        sh_t_list = [clean_val(sht_idx, c) for c in cols_to_scan]

        data["LH Đúng Giờ"] = [(c - t) if pd.notna(c) else np.nan for c, t in zip(lh_c_list, lh_t_list)]
        data["LH Trễ"] = lh_t_list
        data["Shuttle Đúng Giờ"] = [(c - t) if pd.notna(c) else np.nan for c, t in zip(sh_c_list, sh_t_list)]
        data["Shuttle Trễ"] = sh_t_list

        return pd.DataFrame(data), {}

    data_hcm = extract_hub_data(4,5,6,7,17,18,31,38,40,39,41)
    data_bn = extract_hub_data(10,11,12,13,19,20,32,47,49,48,50)

    return data_hcm, data_bn

# ================= FIX MTD =================
def get_last_valid_index(series):
    for i in reversed(range(len(series))):
        if pd.notna(series.iloc[i]) and series.iloc[i] != 0:
            return i
    return -1

def format_vietnam(x):
    if pd.isna(x): return ""
    return f"{x:,.0f}".replace(",", ".")

# ================= UI =================
st.markdown("<h2 style='text-align:center;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)

data_hcm, data_bn = get_data()
df_hcm, _ = data_hcm
df_bn, _ = data_bn

tab1, tab2 = st.tabs(["HCM HUB", "BN HUB"])

def render_dashboard(df):
    if df.empty:
        st.warning("No data")
        return

    # ✅ FIX 2: MTD chỉ tính tới ngày có data
    last_idx = get_last_valid_index(df['Inbound Vol'])
    df_mtd = df.iloc[:last_idx+1] if last_idx >= 0 else df

    t_vin = df_mtd['Inbound Vol'].sum(skipna=True)
    t_vout = df_mtd['Outbound Vol'].sum(skipna=True)
    t_win = df_mtd['Inbound Wgt'].sum(skipna=True)
    t_wout = df_mtd['Outbound Wgt'].sum(skipna=True)
    t_ms = df_mtd['Missort'].sum(skipna=True)
    t_bl = df_mtd['Backlog'].sum(skipna=True)

    lh_total = df_mtd['LH Đúng Giờ'].fillna(0).sum() + df_mtd['LH Trễ'].fillna(0).sum()
    sh_total = df_mtd['Shuttle Đúng Giờ'].fillna(0).sum() + df_mtd['Shuttle Trễ'].fillna(0).sum()

    lhot_mtd = (df_mtd['LH Đúng Giờ'].fillna(0).sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df_mtd['Shuttle Đúng Giờ'].fillna(0).sum() / sh_total * 100) if sh_total > 0 else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Inbound MTD", format_vietnam(t_vin))
    c2.metric("Outbound MTD", format_vietnam(t_vout))
    c3.metric("Missort MTD", format_vietnam(t_ms))
    c4.metric("Backlog MTD", format_vietnam(t_bl))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound"))
    fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound"))
    st.plotly_chart(fig, use_container_width=True)

with tab1:
    render_dashboard(df_hcm)

with tab2:
    render_dashboard(df_bn)
