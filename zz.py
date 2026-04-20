import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CONFIG
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

# CSS giữ nguyên
st.markdown("""<style>
.kpi-table {width:100%;border-collapse:collapse;margin-bottom:30px;background:white;}
.kpi-table th {background:#1f2937;color:white;padding:10px;text-align:center;}
.kpi-table td {padding:10px;border:1px solid #d1d5db;}
.col-pillar {font-weight:bold;text-align:center;background:#f8fafc;}
.col-mtd {font-weight:bold;background:#f0fdf4;}
</style>""", unsafe_allow_html=True)

# 2. TOKEN
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

# 3. DATA
@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers).json()

    vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(r, c):
        try:
            v = vals[r][c]
            s = str(v).replace(",", "").replace("%", "").strip()
            if s in ["", "-", "None"]: return np.nan
            return float(s)
        except:
            return np.nan

    # ===== FIX 1: tìm dynamic ngày =====
    date_row_idx = 3
    start_col_idx = -1
    for c in range(len(vals[date_row_idx])):
        if str(vals[date_row_idx][c]).strip() == "1":
            start_col_idx = c
            break

    num_days = 31
    cols_to_scan = [
        c for c in range(start_col_idx, start_col_idx + num_days)
        if any(pd.notna(clean_val(r, c)) for r in [4,5,6])
    ]

    # ===== FIX 2: tìm cột tuần =====
    weekly_col_idxs = []
    for c in range(len(vals[2])):
        val = str(vals[2][c]).lower()
        if "w" in val or "week" in val:
            weekly_col_idxs.append(c)

    if len(weekly_col_idxs) < 2:
        weekly_col_idxs = list(range(2, 8))  # fallback nhẹ

    def extract(vin, vout, win, wout, ms, ms_rt, bl, lhc, lht, shc, sht):
        df = pd.DataFrame()
        df["Ngày"] = [f"Ngày {i+1}" for i in range(len(cols_to_scan))]
        df["Inbound Vol"] = [clean_val(vin, c) for c in cols_to_scan]
        df["Outbound Vol"] = [clean_val(vout, c) for c in cols_to_scan]
        df["Inbound Wgt"] = [clean_val(win, c) for c in cols_to_scan]
        df["Outbound Wgt"] = [clean_val(wout, c) for c in cols_to_scan]
        df["Missort"] = [clean_val(ms, c) for c in cols_to_scan]
        df["Tỷ lệ Missort (%)"] = [clean_val(ms_rt, c) for c in cols_to_scan]
        df["Backlog"] = [clean_val(bl, c) for c in cols_to_scan]

        lh_c = [clean_val(lhc, c) or 0 for c in cols_to_scan]
        lh_t = [clean_val(lht, c) or 0 for c in cols_to_scan]

        df["LH Đúng Giờ"] = [c - t if c > 0 else np.nan for c, t in zip(lh_c, lh_t)]
        df["LH Trễ"] = [t if t > 0 else np.nan for c, t in zip(lh_c, lh_t)]

        # ===== FIX 3: CW / PW =====
        valid_weeks = [
            idx for idx in weekly_col_idxs
            if pd.notna(clean_val(vin, idx)) and clean_val(vin, idx) > 0
        ]

        cw = valid_weeks[-1] if len(valid_weeks) else -1
        pw = valid_weeks[-2] if len(valid_weeks) > 1 else -1

        summary = {
            "cw_vin": clean_val(vin, cw) if cw != -1 else 0,
            "pw_vin": clean_val(vin, pw) if pw != -1 else 0,

            "cw_vout": clean_val(vout, cw) if cw != -1 else 0,
            "pw_vout": clean_val(vout, pw) if pw != -1 else 0,

            "cw_win": clean_val(win, cw) if cw != -1 else 0,
            "pw_win": clean_val(win, pw) if pw != -1 else 0,

            # FIX BUG CHÍNH
            "cw_wout": clean_val(wout, cw) if cw != -1 else 0,
            "pw_wout": clean_val(wout, pw) if pw != -1 else 0,

            "cw_ms": clean_val(ms, cw) if cw != -1 else 0,
            "pw_ms": clean_val(ms, pw) if pw != -1 else 0,

            "cw_bl": clean_val(bl, cw) if cw != -1 else 0,
            "pw_bl": clean_val(bl, pw) if pw != -1 else 0,
        }

        return df, summary

    data_hcm = extract(4,5,6,7,17,18,31,38,40,39,41)
    data_bn = extract(10,11,12,13,19,20,32,47,49,48,50)

    return data_hcm, data_bn


# ===== UI =====
st.title("J&T KPI Dashboard")

data_hcm, data_bn = get_data()
df, sum_data = data_hcm

# ===== MTD đúng =====
t_vin = df["Inbound Vol"].sum(skipna=True)
t_vout = df["Outbound Vol"].sum(skipna=True)

st.metric("Inbound MTD", f"{t_vin:,.0f}")
st.metric("Outbound MTD", f"{t_vout:,.0f}")

fig = px.line(df, x="Ngày", y=["Inbound Vol", "Outbound Vol"])
st.plotly_chart(fig, use_container_width=True)
