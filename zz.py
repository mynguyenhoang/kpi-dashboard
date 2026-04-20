import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.kpi-table {width:100%;border-collapse:collapse;margin-bottom:30px;background:white;}
.kpi-table th {background:#1f2937;color:white;padding:10px;text-align:center;}
.kpi-table td {padding:10px;border:1px solid #ddd;}
.col-num {text-align:right;font-family:monospace;}
.col-mtd {text-align:right;font-weight:bold;background:#f0fdf4;}
</style>
""", unsafe_allow_html=True)

# =========================
# TOKEN
# =========================
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


# =========================
# GET DATA
# =========================
@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers).json()
    vals = res["data"]["valueRange"]["values"]

    def clean(r, c):
        try:
            v = vals[r][c]
            if v is None:
                return np.nan
            s = str(v).replace("%", "").replace(",", "").strip()
            if s in ["", "-", "#"]:
                return np.nan
            return float(s)
        except:
            return np.nan

    weekly_cols = [3, 4, 5, 6]

    def extract(vin, vout, win, wout, ms, msr, bl):

        days = len(vals[3]) - 6
        cols = list(range(6, 6 + days))

        df = pd.DataFrame({
            "Inbound Vol": [clean(vin, c) for c in cols],
            "Outbound Vol": [clean(vout, c) for c in cols],
            "Inbound Wgt": [clean(win, c) for c in cols],
            "Outbound Wgt": [clean(wout, c) for c in cols],
            "Missort": [clean(ms, c) for c in cols],
            "Backlog": [clean(bl, c) for c in cols],
        })

        # =========================
        # WEEKLY (giữ nguyên logic cũ)
        # =========================
        cw = max([clean(vin, c) for c in weekly_cols if not np.isnan(clean(vin, c))], default=0)
        pw = 0

        # =========================
        # 🔥 FIX CHÍNH: MTD = MONTH COLUMN (KHÔNG SUM DF)
        # =========================
        mt_col = len(vals[0]) - 1

        monthly = {
            "vin": clean(vin, mt_col),
            "vout": clean(vout, mt_col),
            "win": clean(win, mt_col),
            "wout": clean(wout, mt_col),
            "ms": clean(ms, mt_col),
            "bl": clean(bl, mt_col),
        }

        return df, cw, pw, monthly

    return (
        extract(4, 5, 6, 7, 17, 18, 31),
        extract(10, 11, 12, 13, 19, 20, 32)
    )


# =========================
# FORMAT
# =========================
def fmt(x):
    if pd.isna(x):
        return ""
    return f"{x:,.0f}".replace(",", ".")


# =========================
# RENDER
# =========================
def render(df, cw, pw, monthly, color):

    # 🔥 FIX HEADER MTD (đúng MONTH TOTAL)
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Inbound MTD", fmt(monthly["vin"]))
    c2.metric("Outbound MTD", fmt(monthly["vout"]))
    c3.metric("Missort MTD", fmt(monthly["ms"]))
    c4.metric("Backlog MTD", fmt(monthly["bl"]))

    st.markdown("---")


# =========================
# LOAD DATA
# =========================
data_hcm, data_bn = get_data()

df_hcm, cw1, pw1, m1 = data_hcm
df_bn, cw2, pw2, m2 = data_bn

tab1, tab2 = st.tabs(["HCM HUB", "BN HUB"])

with tab1:
    render(df_hcm, cw1, pw1, m1, "#0284c7")

with tab2:
    render(df_bn, cw2, pw2, m2, "#059669")
