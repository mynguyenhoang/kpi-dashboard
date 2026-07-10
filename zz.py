import streamlit.components.v1 as components
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# ════════════════════════════════════════════════════════════
# 1. CẤU HÌNH TRANG & CSS
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="J&T Cargo · KPI Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
/* ─── RESET & BASE ─────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
:root {
    --navy:       #0B1437;
    --navy-mid:   #112060;
    --blue:       #1a56db;
    --blue-light: #3b82f6;
    --surface:    #ffffff;
    --surface-2:  #f4f7fe;
    --border:     #e8edf9;
    --text-main:  #0b1437;
    --text-muted: #5a6585;
    --green:      #05c168;
    --green-bg:   #ecfdf5;
    --green-txt:  #065f46;
    --red:        #f04438;
    --red-bg:     #fef2f2;
    --red-txt:    #b91c1c;
    --amber:      #f79009;
    --amber-bg:   #fffbeb;
    --purple:     #7c3aed;
    --shadow-sm:  0 1px 3px rgba(11,20,55,.08), 0 1px 2px rgba(11,20,55,.06);
    --shadow-md:  0 4px 16px rgba(11,20,55,.10), 0 2px 6px rgba(11,20,55,.06);
    --shadow-lg:  0 12px 32px rgba(11,20,55,.14), 0 4px 12px rgba(11,20,55,.08);
    --radius:     14px;
    --radius-sm:  8px;
    --font:       'Nunito', sans-serif;
    --font-mono:  'JetBrains Mono', monospace;
}

/* ─── APP BACKGROUND ───────────────────────────────────── */
.stApp, [data-testid="stAppViewContainer"] {
    background: var(--surface-2) !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 16px !important;
}
body, p, div, span, td, th, label, input, button {
    font-family: 'Nunito', sans-serif !important;
}

/* ─── HIDE STREAMLIT CHROME ────────────────────────────── */
#MainMenu, header, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stHeader"] {
    visibility: hidden !important;
    height: 0 !important;
}

/* ─── MAIN HEADER BANNER ───────────────────────────────── */
.dashboard-header {
    background: linear-gradient(135deg, #0B1437 0%, #1a3a8f 50%, #0284c7 100%);
    border-radius: 20px;
    padding: 36px 48px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
}
.dashboard-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: rgba(255,255,255,.05);
}
.dashboard-header::after {
    content: '';
    position: absolute;
    bottom: -40px; left: 30%;
    width: 180px; height: 180px;
    border-radius: 50%;
    background: rgba(255,255,255,.04);
}
.header-title {
    font-size: 40px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.5px;
    margin: 0 0 8px;
    line-height: 1.15;
}
.header-subtitle {
    font-size: 16px;
    color: rgba(255,255,255,.65);
    font-weight: 500;
    margin: 0;
}

/* ─── TABS ─────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-radius: var(--radius) !important;
    padding: 6px !important;
    gap: 4px !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid var(--border) !important;
    margin-bottom: 20px !important;
}
button[data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 11px 26px !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 800 !important;
    font-size: 16px !important;
    transition: all .2s ease !important;
}
button[data-baseweb="tab"] div {
    color: var(--text-muted) !important;
    font-weight: 800 !important;
    font-size: 16px !important;
    font-family: 'Nunito', sans-serif !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, var(--navy) 0%, var(--blue) 100%) !important;
    box-shadow: 0 4px 12px rgba(26,86,219,.35) !important;
}
button[data-baseweb="tab"][aria-selected="true"] div {
    color: #fff !important;
}

/* ─── METRIC CARDS ─────────────────────────────────────── */
div[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 22px 20px 18px !important;
    box-shadow: var(--shadow-sm) !important;
    transition: box-shadow .25s ease, transform .25s ease !important;
    position: relative !important;
    overflow: hidden !important;
}
div[data-testid="metric-container"]:hover {
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-3px) !important;
}
div[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--blue) 0%, var(--blue-light) 100%);
    border-radius: var(--radius) var(--radius) 0 0;
}
div[data-testid="metric-container"] label {
    font-family: 'Nunito', sans-serif !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    color: var(--text-muted) !important;
    letter-spacing: .3px !important;
    text-transform: uppercase !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 32px !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
    letter-spacing: -1px !important;
}

/* ─── SECTION HEADERS ──────────────────────────────────── */
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 36px 0 20px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
}
.section-header-text {
    font-size: 22px;
    font-weight: 900;
    color: var(--navy);
    letter-spacing: -.3px;
    font-family: 'Nunito', sans-serif !important;
}
.section-header-sub {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-muted);
    font-family: 'Nunito', sans-serif !important;
}

/* ─── KPI TABLE ─────────────────────────────────────────── */
.kpi-wrap {
    background: var(--surface);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    overflow: hidden;
    border: 1px solid var(--border);
    margin-bottom: 28px;
}
.kpi-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font);
}
.kpi-table thead tr {
    background: linear-gradient(135deg, var(--navy) 0%, #1a3a8f 100%);
}
.kpi-table th {
    color: rgba(255,255,255,.95) !important;
    padding: 17px 14px;
    text-align: center;
    font-size: 14px !important;
    font-weight: 800 !important;
    letter-spacing: .4px;
    text-transform: uppercase;
    border: none !important;
    white-space: nowrap;
    font-family: 'Nunito', sans-serif !important;
}
.kpi-table th:first-child { text-align: left; }
.kpi-table tbody tr { transition: background .15s; }
.kpi-table tbody tr:hover { background: #f0f5ff; }
.kpi-table td {
    padding: 15px 14px;
    border-bottom: 1px solid var(--border);
    border-right: none;
    font-size: 16px;
    color: var(--text-main);
    vertical-align: middle;
    font-family: 'Nunito', sans-serif !important;
}
.kpi-table tbody tr:last-child td { border-bottom: none; }

/* Pillar cells */
.col-pillar {
    font-weight: 900 !important;
    font-size: 13px !important;
    text-align: center !important;
    background: var(--surface-2) !important;
    color: var(--navy) !important;
    letter-spacing: .3px;
    border-right: 1px solid var(--border) !important;
    white-space: nowrap;
    font-family: 'Nunito', sans-serif !important;
}
/* Metric name */
.col-metric {
    font-weight: 700 !important;
    color: #1e293b !important;
    font-size: 16px !important;
    border-right: 1px solid var(--border) !important;
    min-width: 230px;
    font-family: 'Nunito', sans-serif !important;
}
/* Numbers */
.col-num {
    text-align: right !important;
    font-family: var(--font-mono) !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
    white-space: nowrap;
}
/* MTD highlight */
.col-mtd {
    text-align: right !important;
    font-family: var(--font-mono) !important;
    font-size: 20px !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #ecfdf5, #d1fae5) !important;
    color: #065f46 !important;
    border-left: 3px solid var(--green) !important;
    white-space: nowrap;
}

/* ─── SCROLLBAR ─────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c7d2e8; border-radius: 99px; }

.js-plotly-plot { border-radius: var(--radius); overflow: hidden; }

/* ─── EXPANDER FIX ──────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-sm) !important;
    margin-top: 16px !important;
}
[data-testid="stExpander"] details summary {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    padding: 12px 16px !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
    list-style: none !important;
}
[data-testid="stExpander"] details summary svg {
    flex-shrink: 0 !important;
    margin-right: 4px !important;
}
[data-testid="stExpander"] details summary p {
    margin: 0 !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
}
/* Fix dataframe font inside expander */
[data-testid="stExpander"] .stDataFrame,
[data-testid="stExpander"] table,
[data-testid="stExpander"] td,
[data-testid="stExpander"] th {
    font-family: 'Nunito', sans-serif !important;
    font-size: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
# ════════════════════════════════════════════════════════════
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except Exception as e:
        st.error(f"🔴 Lỗi lấy Token Feishu: {str(e)}")
        return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("🔴 Không lấy được Token API Feishu.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ85?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    res_data = None

    for attempt in range(5):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            elif "not ready" in str(res.get("msg")).lower():
                if attempt < 4:
                    time.sleep(5)
                    continue
                else:
                    st.error("🔴 API Feishu báo 'Not ready' quá lâu.")
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else:
                st.error(f"🔴 Lỗi từ Feishu API: {res.get('msg')}")
                return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception as e:
            st.error(f"🔴 Lỗi kết nối: {str(e)}")
            return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not res_data:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals:
        st.error("🔴 File Feishu trống!")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if len(vals) < 80:
        st.error(f"🔴 File chỉ có {len(vals)} dòng, cần ít nhất 80.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v:
                    return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-':
                    return 0.0
                return float(s)
            return np.nan
        except:
            return np.nan

    try:
        weekly_col_idxs = [3, 4, 5, 6]
        date_row_idx = 3
        start_col_idx = -1
        for c in range(2, len(vals[date_row_idx])):
            val = str(vals[date_row_idx][c]).strip()
            if val == "1":
                start_col_idx = c
                break

        num_days = 26
        if start_col_idx != -1:
            max_day = 1
            for c in range(start_col_idx, len(vals[date_row_idx])):
                val = str(vals[date_row_idx][c]).strip()
                if val.isdigit():
                    max_day = max(max_day, int(val))
            num_days = max_day
        else:
            start_col_idx = 6

        cols_to_scan = [start_col_idx + i for i in range(num_days)]

        def extract_hub_data(
            vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx,
            bl_idx, bl_24h_idx,
            cot_total_idx, cot_ontime_idx,
            cot_total_1am_idx, cot_ontime_1am_idx, cot_rate_1am_idx,
            shc_idx, lhc_idx, sht_idx, lht_idx
        ):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
            data["Inbound Vol"]        = [clean_val(vin_idx, c)        for c in cols_to_scan]
            data["Outbound Vol"]       = [clean_val(vout_idx, c)       for c in cols_to_scan]
            data["Inbound Wgt"]        = [clean_val(win_idx, c)        for c in cols_to_scan]
            data["Outbound Wgt"]       = [clean_val(wout_idx, c)       for c in cols_to_scan]
            data["Total Process Vol"]  = [clean_val(tproc_vol_idx, c)  for c in cols_to_scan]
            data["Total Process Wgt"]  = [clean_val(tproc_wgt_idx, c)  for c in cols_to_scan]
            data["Backlog"]            = [clean_val(bl_idx, c)         for c in cols_to_scan]
            data["Backlog 24H"]        = [clean_val(bl_24h_idx, c)     for c in cols_to_scan]
            data["COT Total"]          = [clean_val(cot_total_idx, c)  for c in cols_to_scan]
            data["COT Ontime"]         = [clean_val(cot_ontime_idx, c) for c in cols_to_scan]
            data["COT Rate (%)"]       = [
                (o / t * 100) if (t and t > 0) else np.nan
                for t, o in zip(data["COT Total"], data["COT Ontime"])
            ]
            data["COT 1AM Total"]      = [clean_val(cot_total_1am_idx, c)  for c in cols_to_scan]
            data["COT 1AM Ontime"]     = [clean_val(cot_ontime_1am_idx, c) for c in cols_to_scan]
            data["COT 1AM Rate (%)"]   = [
                val if pd.notna(val) else ((o / t * 100) if (t and t > 0) else np.nan)
                for t, o, val in zip(
                    data["COT 1AM Total"], data["COT 1AM Ontime"],
                    [clean_val(cot_rate_1am_idx, c) for c in cols_to_scan]
                )
            ]
            data["Shuttle Chuyến"]     = [clean_val(shc_idx, c) for c in cols_to_scan]
            data["Linehaul Chuyến"]    = [clean_val(lhc_idx, c) for c in cols_to_scan]
            data["Shuttle Late"]       = [clean_val(sht_idx, c) for c in cols_to_scan]
            data["Linehaul Late"]      = [clean_val(lht_idx, c) for c in cols_to_scan]
            data["LH Rate (%)"]        = [
                (c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan
                for c, t in zip(data["Linehaul Chuyến"], data["Linehaul Late"])
            ]
            data["SH Rate (%)"]        = [
                (c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan
                for c, t in zip(data["Shuttle Chuyến"], data["Shuttle Late"])
            ]

            valid_weeks = [
                idx for idx in weekly_col_idxs
                if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0
            ]
            cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
            pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

            def get_rate(num_idx, den_idx, col_idx):
                if col_idx == -1: return 0
                n = clean_val(num_idx, col_idx)
                d = clean_val(den_idx, col_idx)
                return (n / d * 100) if (d and d > 0) else 0

            def lhot(idx):
                if idx == -1: return 0
                lhc = clean_val(lhc_idx, idx)
                lht = clean_val(lht_idx, idx)
                return (lhc - lht) / lhc * 100 if lhc and lhc > 0 else 0

            def shot(idx):
                if idx == -1: return 0
                shc = clean_val(shc_idx, idx)
                sht = clean_val(sht_idx, idx)
                return (shc - sht) / shc * 100 if shc and shc > 0 else 0

            weekly_summary = {
                "cw_vin":       clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_vin":       clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_vout":      clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_vout":      clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_tproc_wgt": clean_val(tproc_wgt_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_tproc_wgt": clean_val(tproc_wgt_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_bl":        clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_bl":        clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_bl_24h":    clean_val(bl_24h_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_bl_24h":    clean_val(bl_24h_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_cot_ontime": clean_val(cot_ontime_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_cot_ontime": clean_val(cot_ontime_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_lhot": lhot(cw_idx), "pw_lhot": lhot(pw_idx),
                "cw_shot": shot(cw_idx), "pw_shot": shot(pw_idx),
                "cw_cot": get_rate(cot_ontime_idx, cot_total_idx, cw_idx),
                "pw_cot": get_rate(cot_ontime_idx, cot_total_idx, pw_idx),
            }
            return pd.DataFrame(data), weekly_summary

        data_hcm = extract_hub_data(
            vin_idx=4,  vout_idx=5,  win_idx=6,  wout_idx=7,
            tproc_vol_idx=8,  tproc_wgt_idx=9,
            bl_idx=35, bl_24h_idx=36,
            cot_total_idx=46,    cot_ontime_idx=47,
            cot_total_1am_idx=49, cot_ontime_1am_idx=50, cot_rate_1am_idx=51,
            shc_idx=52, lhc_idx=53, sht_idx=54, lht_idx=55,
        )
        data_bn = extract_hub_data(
            vin_idx=10, vout_idx=11, win_idx=12, wout_idx=13,
            tproc_vol_idx=14, tproc_wgt_idx=15,
            bl_idx=38, bl_24h_idx=39,
            cot_total_idx=58,    cot_ontime_idx=59,
            cot_total_1am_idx=61, cot_ontime_1am_idx=62, cot_rate_1am_idx=63,
            shc_idx=64, lhc_idx=65, sht_idx=66, lht_idx=67,
        )
        data_sh = extract_hub_data(
            vin_idx=16, vout_idx=17, win_idx=18, wout_idx=19,
            tproc_vol_idx=20, tproc_wgt_idx=21,
            bl_idx=41, bl_24h_idx=42,
            cot_total_idx=70,    cot_ontime_idx=71,
            cot_total_1am_idx=73, cot_ontime_1am_idx=74, cot_rate_1am_idx=75,
            shc_idx=76, lhc_idx=77, sht_idx=78, lht_idx=79,
        )
        return data_hcm, data_bn, data_sh

    except Exception as e:
        st.error(f"🔴 Lỗi xử lý dữ liệu: {str(e)}")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

# ════════════════════════════════════════════════════════════
# 3. TIỆN ÍCH ĐỊNH DẠNG
# ════════════════════════════════════════════════════════════
_IFRAME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{background:transparent;font-family:'Nunito',sans-serif;font-size:16px}
:root{
  --navy:#0B1437;--blue:#1a56db;--surface:#ffffff;--surface-2:#f4f7fe;
  --border:#e8edf9;--text-main:#0b1437;--text-muted:#5a6585;
  --green:#05c168;--green-bg:#ecfdf5;--green-txt:#065f46;
  --red:#f04438;--font:'Nunito',sans-serif;--font-mono:'JetBrains Mono',monospace;
}
.kpi-wrap{background:#fff;border-radius:14px;box-shadow:0 4px 16px rgba(11,20,55,.10);overflow:hidden;border:1px solid #e8edf9}
.kpi-table{width:100%;border-collapse:collapse;font-family:'Nunito',sans-serif}
.kpi-table thead tr{background:linear-gradient(135deg,#0B1437 0%,#1a3a8f 100%)}
.kpi-table th{color:rgba(255,255,255,.95);padding:16px 14px;text-align:center;font-size:14px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;border:none;white-space:nowrap;font-family:'Nunito',sans-serif}
.kpi-table th:first-child{text-align:left}
.kpi-table tbody tr:hover{background:#f0f5ff}
.kpi-table td{padding:15px 14px;border-bottom:1px solid #e8edf9;font-size:16px;color:#0b1437;vertical-align:middle;font-family:'Nunito',sans-serif}
.kpi-table tbody tr:last-child td{border-bottom:none}
.col-pillar{font-weight:900;font-size:13px;text-align:center;background:#f4f7fe;letter-spacing:.3px;border-right:1px solid #e8edf9;white-space:nowrap;font-family:'Nunito',sans-serif}
.col-metric{font-weight:700;color:#1e293b;font-size:16px;border-right:1px solid #e8edf9;min-width:230px;font-family:'Nunito',sans-serif}
.col-num{text-align:right;font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:600;color:#0b1437;white-space:nowrap}
.col-mtd{text-align:right;font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:800;background:linear-gradient(135deg,#ecfdf5,#d1fae5);color:#065f46;border-left:3px solid #05c168;white-space:nowrap}
.section-header{display:flex;align-items:center;gap:10px;padding:14px 2px 12px;border-bottom:1px solid #e8edf9;margin-bottom:4px}
.section-header-text{font-size:20px;font-weight:900;color:#0b1437;letter-spacing:-.3px;font-family:'Nunito',sans-serif}
.section-header-sub{font-size:14px;font-weight:600;color:#5a6585;margin-top:2px;font-family:'Nunito',sans-serif}
"""

def _html(html_body: str, height: int = 500):
    full = f"<!DOCTYPE html><html><head><style>{_IFRAME_CSS}</style></head><body>{html_body}</body></html>"
    components.html(full, height=height, scrolling=False)

def fmt_vn(number):
    if pd.isna(number) or number == "":
        return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) and pd.isna(prev):
        return "<td style='text-align:center'>—</td><td class='col-num'></td><td class='col-num'></td>"
    if pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct and pd.notna(cur) else fmt_vn(cur)
        if pd.isna(cur): cur_str = "—"
        return f"<td style='text-align:center;color:#94a3b8;font-size:14px'>—</td><td class='col-num'>{cur_str}</td><td class='col-num'>—</td>"
    if pd.isna(cur):
        prev_str = f"{prev:.2f}%" if is_pct else fmt_vn(prev)
        return f"<td style='text-align:center;color:#94a3b8;font-size:14px'>—</td><td class='col-num'>—</td><td class='col-num'>{prev_str}</td>"

    diff = cur - prev
    pct  = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    is_positive = diff > 0
    good = (is_positive and not inverse) or (not is_positive and inverse)

    if diff > 0:
        bg = "#ecfdf5" if good else "#fef2f2"
        tc = "#065f46" if good else "#b91c1c"
        border = "#86efac" if good else "#fca5a5"
        sign = "+"
        arrow = "▲"
    elif diff < 0:
        bg = "#fef2f2" if good else "#ecfdf5"
        tc = "#b91c1c" if good else "#065f46"
        border = "#fca5a5" if good else "#86efac"
        sign = ""
        arrow = "▼"
    else:
        bg = "#f1f5f9"; tc = "#64748b"; border = "#cbd5e1"; sign = ""; arrow = "●"

    wow_str = f"{arrow} {sign}{pct:.1f}%" if not is_pct else f"{arrow} {sign}{diff:.1f}%"
    cur_str  = fmt_vn(cur) if not is_pct else f"{cur:.2f}%"
    prev_str = fmt_vn(prev) if not is_pct else f"{prev:.2f}%"

    return (
        f"<td style='background:{bg};color:{tc};font-weight:900;text-align:center;"
        f"font-size:15px;border-radius:8px;white-space:nowrap;"
        f"font-family:JetBrains Mono,monospace;"
        f"border:1px solid {border};padding:7px 12px'>{wow_str}</td>"
        f"<td class='col-num'>{cur_str}</td>"
        f"<td class='col-num'>{prev_str}</td>"
    )

# ════════════════════════════════════════════════════════════
# 4. CHART THEME
# ════════════════════════════════════════════════════════════
CHART_FONT = dict(family="Nunito, sans-serif", size=15, color="#0b1437")

def clean_layout(fig, title, height=480):
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family="Nunito, sans-serif", size=15, color="#0b1437"),
            x=0, xanchor='left', pad=dict(l=4, t=6),
            yref='paper', y=1, yanchor='bottom',
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=72, b=70, l=8, r=8),
        height=height,
        font=CHART_FONT,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=10, color="#5a6585", family="Nunito, sans-serif"),
            tickangle=-90,
            nticks=16,
            linecolor="#e8edf9",
            showline=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f0f4ff",
            gridwidth=1,
            tickfont=dict(size=13, color="#5a6585", family="Nunito, sans-serif"),
            zeroline=False,
        ),
        hoverlabel=dict(
            font=dict(family="Nunito, sans-serif", size=14),
            bgcolor="white",
            bordercolor="#e8edf9",
        ),
        legend=dict(
            font=dict(family="Nunito, sans-serif", size=13),
            bgcolor="rgba(255,255,255,.9)",
            bordercolor="#e8edf9",
            borderwidth=1,
            orientation="h",
            x=0, y=1.18,          # legend nằm trên title, không đè nhau
            xanchor="left",
            yanchor="bottom",
        )
    )
    fig.update_traces(cliponaxis=False)
    return fig

# ════════════════════════════════════════════════════════════
# 5. MAIN RENDER
# ════════════════════════════════════════════════════════════
def get_last_7_days(df):
    if df.empty: return df
    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    if valid_df.empty: return df.tail(7).reset_index(drop=True)
    last_idx  = valid_df.index[-1]
    start_idx = max(0, last_idx - 6)
    return df.iloc[start_idx:last_idx+1].reset_index(drop=True)

def render_dashboard(df, summary, accent_color, hub_name, period_label="MTD",
                     show_weekly=True, num_daily_cols=3, show_raw_data=False):
    if df.empty: return

    valid_df   = df.dropna(subset=['Inbound Vol'])
    valid_df   = valid_df[valid_df['Inbound Vol'] > 0]
    actual_cols = min(len(valid_df), num_daily_cols)
    data_slice  = valid_df.tail(actual_cols + 1).reset_index(drop=True)

    if len(data_slice) > actual_cols:
        d_names = data_slice['Ngày'].tolist()[1:]
    else:
        d_names = data_slice['Ngày'].tolist()

    pad_len   = num_daily_cols - len(d_names)
    d_display = ["-"] * pad_len + d_names

    # ── Daily trend cells (badge-style indicators) ──────────
    def get_d(col_name, is_pct=False, inverse=False):
        vals_list = data_slice[col_name].tolist()
        if len(vals_list) > actual_cols:
            cur_vals  = vals_list[1:]
            prev_vals = vals_list[:-1]
        else:
            cur_vals  = vals_list
            prev_vals = [np.nan] + vals_list[:-1]

        cur_vals  = [np.nan] * pad_len + cur_vals
        prev_vals = [np.nan] * pad_len + prev_vals

        cells = []
        for i in range(num_daily_cols):
            cur  = cur_vals[i]
            prev = prev_vals[i]

            if pd.isna(cur):
                cells.append("<td class='col-num' style='color:#cbd5e1'>—</td>")
                continue

            cur_str = f"{cur:.1f}%" if is_pct else fmt_vn(cur)
            bg_cell = "#f8fafc" if i % 2 == 0 else "white"

            if pd.notna(prev) and prev != cur:
                diff     = cur - prev
                going_up = diff > 0
                good     = (going_up and not inverse) or (not going_up and inverse)
                arrow    = "▲" if going_up else "▼"
                badge_bg  = "#ecfdf5" if good else "#fef2f2"
                badge_col = "#065f46" if good else "#b91c1c"
                badge_bdr = "#86efac" if good else "#fca5a5"

                badge = (
                    f"<span style='display:inline-block;background:{badge_bg};color:{badge_col};"
                    f"border:1px solid {badge_bdr};padding:3px 10px;border-radius:99px;"
                    f"font-size:14px;font-weight:800;margin-left:6px;"
                    f"font-family:JetBrains Mono,monospace'>{arrow}</span>"
                )
                styled = (
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:16px;"
                    f"font-weight:700;color:#0b1437'>{cur_str}</span>{badge}"
                )
            else:
                styled = (
                    f"<span style='font-family:JetBrains Mono,monospace;font-size:16px;"
                    f"font-weight:700;color:#0b1437'>{cur_str}</span>"
                )

            cells.append(f"<td class='col-num' style='background:{bg_cell}'>{styled}</td>")
        return "".join(cells)

    # ── MTD aggregates ──────────────────────────────────────
    t_vin          = df['Inbound Vol'].sum(skipna=True)
    t_vout         = df['Outbound Vol'].sum(skipna=True)
    t_tproc_vol    = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt    = df['Total Process Wgt'].sum(skipna=True)
    t_bl           = df['Backlog'].sum(skipna=True)
    t_bl_24h       = df['Backlog 24H'].sum(skipna=True)
    cot_ontime_mtd = df['COT Ontime'].sum(skipna=True)
    lh_tot   = df['Linehaul Chuyến'].fillna(0).sum()
    lh_late  = df['Linehaul Late'].fillna(0).sum()
    lhot_mtd = (lh_tot - lh_late) / lh_tot * 100 if lh_tot > 0 else 0
    sh_tot   = df['Shuttle Chuyến'].fillna(0).sum()
    sh_late  = df['Shuttle Late'].fillna(0).sum()
    shot_mtd = (sh_tot - sh_late) / sh_tot * 100 if sh_tot > 0 else 0
    cot_mtd  = df['COT Ontime'].sum() / df['COT Total'].sum() * 100 if df['COT Total'].sum() > 0 else 0

    # ── 5 Summary cards ────────────────────────────────────
    CARDS = [
        ("Inbound",          "入库",   t_vin,        period_label, "#1a56db"),
        ("Outbound",         "出库",   t_vout,       period_label, "#059669"),
        ("Tổng đơn xử lý",  "总处理量", t_tproc_vol, period_label, "#7c3aed"),
        ("Trọng lượng (kg)", "重量",   t_tproc_wgt, period_label, "#0284c7"),
        ("Backlog",          "积压",   t_bl,         period_label, "#ef4444"),
    ]
    cols = st.columns(5)
    for col_obj, (vn, cn, val, lbl, color) in zip(cols, CARDS):
        with col_obj:
            st.markdown(f"""
            <div style="
                background:white;
                border:1px solid #e8edf9;
                border-top:4px solid {color};
                border-radius:14px;
                padding:22px 20px 18px;
                box-shadow:0 2px 8px rgba(11,20,55,.07);
                font-family:'Nunito',sans-serif;
            ">
                <div style="font-size:13px;font-weight:800;color:#8896b3;
                    text-transform:uppercase;letter-spacing:.4px;margin-bottom:10px;
                    font-family:'Nunito',sans-serif">
                    {vn} · {cn}
                    <span style="background:{color}22;color:{color};
                    padding:2px 9px;border-radius:99px;font-size:12px;margin-left:5px;
                    font-weight:700">{lbl}</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:30px;
                    font-weight:700;color:#0b1437;letter-spacing:-1px;line-height:1">
                    {fmt_vn(val)}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI Table ───────────────────────────────────────────
    header_wow = (
        '<th style="min-width:110px">WOW</th>'
        '<th style="min-width:100px">Tuần này</th>'
        '<th style="min-width:100px">Tuần trước</th>'
    ) if show_weekly else ""

    daily_hdrs = "".join(
        [f"<th style='background:rgba(255,255,255,.12);min-width:100px'>{d}</th>"
         for d in d_display]
    )

    def build_row(kpi_title, rowspan, kpi_color, metric_name,
                  wow_cur, wow_prev, mtd_val, col_name,
                  is_pct=False, inverse=False, is_first=False):
        kpi_td = (
            f'<td rowspan="{rowspan}" class="col-pillar" '
            f'style="border-left:4px solid {kpi_color};color:{kpi_color};font-size:13px">'
            f'{kpi_title}</td>'
        ) if is_first else ''
        wow_td  = get_wow_cell(wow_cur, wow_prev, is_pct, inverse) if show_weekly else ''
        mtd_str = f"{mtd_val:.1f}%" if is_pct else fmt_vn(mtd_val)
        d_tds   = get_d(col_name, is_pct, inverse)
        return (
            f"<tr>{kpi_td}"
            f"<td class='col-metric'>{metric_name}</td>"
            f"{wow_td}"
            f"<td class='col-mtd'>{mtd_str}</td>"
            f"{d_tds}</tr>"
        )

    rows = [
        build_row("Sản Lượng<br>生产", 3, "#1a56db",
                  "Inbound (đơn) | 入库单量",
                  summary['cw_vin'], summary['pw_vin'], t_vin, 'Inbound Vol', is_first=True),
        build_row("", 0, "", "Outbound (đơn) | 出库单量",
                  summary['cw_vout'], summary['pw_vout'], t_vout, 'Outbound Vol'),
        build_row("", 0, "", "Trọng lượng (kg) | 重量",
                  summary['cw_tproc_wgt'], summary['pw_tproc_wgt'], t_tproc_wgt, 'Total Process Wgt'),
        
        build_row("Chất Lượng<br>质量", 4, "#ef4444",
                  "Backlog (đơn) | 积压单量",
                  summary['cw_bl'], summary['pw_bl'], t_bl, 'Backlog', inverse=True, is_first=True),
        build_row("", 0, "", "Backlog >24H | 超24H积压",
                  summary['cw_bl_24h'], summary['pw_bl_24h'], t_bl_24h, 'Backlog 24H', inverse=True),
        build_row("", 0, "", "Đơn gửi đúng COT | 准时出库量",
                  summary['cw_cot_ontime'], summary['pw_cot_ontime'], cot_ontime_mtd, 'COT Ontime'),
        build_row("", 0, "", "% Sent Volume Ontime | 准时率",
                  summary['cw_cot'], summary['pw_cot'], cot_mtd, 'COT Rate (%)', is_pct=True),
        
        build_row("Vận Tải<br>运输", 2, "#059669",
                  "Linehaul đúng COT (%) | 干线准时率",
                  summary['cw_lhot'], summary['pw_lhot'], lhot_mtd, 'LH Rate (%)', is_pct=True, is_first=True),
        build_row("", 0, "", "Shuttle đúng COT (%) | 摆渡准时率",
                  summary['cw_shot'], summary['pw_shot'], shot_mtd, 'SH Rate (%)', is_pct=True),
    ]

    _thead = (
        f'<th style="text-align:left;width:90px">KPI</th>'
        f'<th style="text-align:left">Hạng mục | 指标名称</th>'
        f'{header_wow}'
        f'<th style="min-width:120px">{period_label} | 累计</th>'
        f'{daily_hdrs}'
    )
    _tbody = "".join(rows)
    _html(
        f'<div class="kpi-wrap"><table class="kpi-table">'
        f'<thead><tr>{_thead}</tr></thead>'
        f'<tbody>{_tbody}</tbody></table></div>',
        height=530
    )

    # ══════════════════════════
    # SECTION 1 · SẢN LƯỢNG
    # ══════════════════════════
    _html(
        '<div class="section-header"><div>'
        '<div class="section-header-text">Sản Lượng &amp; Năng Suất · 生产与产能</div>'
        '<div class="section-header-sub">Inbound / Outbound / Trọng lượng hàng ngày</div>'
        '</div></div>',
        height=68
    )

    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Ngày'], y=df['Inbound Vol'], name="Inbound",
            fill='tozeroy', mode='lines+markers',
            line=dict(color='#1a56db', width=3),
            marker=dict(size=6, color='#1a56db'),
            fillcolor='rgba(26,86,219,.08)',
        ))
        fig.add_trace(go.Scatter(
            x=df['Ngày'], y=df['Outbound Vol'], name="Outbound",
            mode='lines+markers',
            line=dict(color='#f59e0b', width=3, dash='dot'),
            marker=dict(size=6, color='#f59e0b'),
        ))
        fig = clean_layout(fig, "Inbound & Outbound | 每日入库/出库")
        st.plotly_chart(fig, use_container_width=True, key=f"{hub_name}_{period_label}_fig1")

    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df['Ngày'], y=df['Total Process Vol'],
            marker=dict(
                color=df['Total Process Vol'],
                colorscale=[[0, '#bfdbfe'], [1, '#1a56db']],
                showscale=False,
            ),
            text=[fmt_vn(v) if pd.notna(v) and v > 0 else "" for v in df['Total Process Vol']],
            textposition='inside', textangle=-90,
            insidetextanchor='end',
            textfont=dict(size=13, color='white', family="JetBrains Mono"),
        ))
        fig2 = clean_layout(fig2, "Năng suất (Số đơn) | 产能单数")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, key=f"{hub_name}_{period_label}_fig2")

    with col3:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=df['Ngày'], y=df['Total Process Wgt'],
            marker=dict(
                color=df['Total Process Wgt'],
                colorscale=[[0, '#ddd6fe'], [1, '#7c3aed']],
                showscale=False,
            ),
            text=[fmt_vn(v) if pd.notna(v) and v > 0 else "" for v in df['Total Process Wgt']],
            textposition='inside', textangle=-90,
            insidetextanchor='end',
            textfont=dict(size=13, color='white', family="JetBrains Mono"),
        ))
        fig3 = clean_layout(fig3, "Năng suất (Kg) | 产能重量")
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True, key=f"{hub_name}_{period_label}_fig3")

    # ══════════════════════════
    # SECTION 2 · VẬN TẢI & COT
    # ══════════════════════════
    _html(
        '<div class="section-header"><div>'
        '<div class="section-header-text">Vận Tải &amp; COT · 运输与准时出库管理</div>'
        '<div class="section-header-sub">Linehaul / Shuttle / Sent Volume Ontime</div>'
        '</div></div>',
        height=68
    )

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=df['Ngày'], y=df['Shuttle Chuyến'], name="Shuttle",
            marker_color='#3b82f6',
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Shuttle Chuyến']],
            textposition='inside', textfont=dict(size=13, color='white', weight='bold'),
        ))
        fig4.add_trace(go.Bar(
            x=df['Ngày'], y=df['Linehaul Chuyến'], name="Linehaul",
            marker_color='#f97316',
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Linehaul Chuyến']],
            textposition='inside', textfont=dict(size=13, color='white', weight='bold'),
        ))
        fig4 = clean_layout(fig4, "Số chuyến Shuttle/LH | 总车次")
        fig4.update_layout(barmode='stack')
        st.plotly_chart(fig4, use_container_width=True, key=f"{hub_name}_{period_label}_fig4")

    with col_t2:
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=df['Ngày'], y=df['COT Total'], name="Tổng đơn",
            marker_color='#bfdbfe', opacity=0.7,
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['COT Ontime']],
            textposition='inside', textangle=-90, insidetextanchor='end',
            textfont=dict(size=12, color='#1e3a8a'),
        ))
        fig5.add_trace(go.Scatter(
            x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ %",
            yaxis="y2",
            line=dict(color='#059669', width=3),
            mode='lines+markers+text',
            marker=dict(size=7, color='#059669'),
            text=[f"{v:.0f}%" if pd.notna(v) and v > 0 else "" for v in df['COT Rate (%)']],
            textposition="top center",
            textfont=dict(size=14, color='#065f46', family="JetBrains Mono"),
        ))
        fig5 = clean_layout(fig5, "% Sent Volume Ontime | 准时出库率")
        fig5.update_layout(
            showlegend=False,
            yaxis2=dict(overlaying='y', side='right', range=[0, 115],
                        showgrid=False, tickfont=dict(size=13, color='#059669'))
        )
        st.plotly_chart(fig5, use_container_width=True, key=f"{hub_name}_{period_label}_fig5")

    with col_t3:
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            x=df['Ngày'], y=df['COT 1AM Total'], name="Tổng 1AM",
            marker_color='#fed7aa', opacity=0.7,
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['COT 1AM Ontime']],
            textposition='inside', textangle=-90, insidetextanchor='end',
            textfont=dict(size=12, color='#7c2d12'),
        ))
        fig6.add_trace(go.Scatter(
            x=df['Ngày'], y=df['COT 1AM Rate (%)'], name="Tỷ lệ 1AM",
            yaxis="y2",
            line=dict(color='#ea580c', width=3),
            mode='lines+markers+text',
            marker=dict(size=7, color='#ea580c'),
            text=[f"{v:.0f}%" if pd.notna(v) and v > 0 else "" for v in df['COT 1AM Rate (%)']],
            textposition="top center",
            textfont=dict(size=14, color='#7c2d12', family="JetBrains Mono"),
        ))
        fig6 = clean_layout(fig6, "% Sent Volume 1AM | 1AM准时率")
        fig6.update_layout(
            showlegend=False,
            yaxis2=dict(overlaying='y', side='right', range=[0, 115],
                        showgrid=False, tickfont=dict(size=13, color='#ea580c'))
        )
        st.plotly_chart(fig6, use_container_width=True, key=f"{hub_name}_{period_label}_fig6")

    col_l1, col_l2, col_l3 = st.columns([1, 1, 1.2])
    with col_l1:
        fig7 = go.Figure()
        fig7.add_trace(go.Bar(
            x=df['Ngày'], y=df['Shuttle Late'],
            marker=dict(color='#ef4444', line=dict(color='#b91c1c', width=1)),
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Shuttle Late']],
            textposition='outside',
            textfont=dict(size=14, color='#b91c1c', family="JetBrains Mono"),
        ))
        fig7 = clean_layout(fig7, "Shuttle Late | 支线延迟", height=380)
        fig7.update_layout(showlegend=False)
        st.plotly_chart(fig7, use_container_width=True, key=f"{hub_name}_{period_label}_fig7")

    with col_l2:
        fig8 = go.Figure()
        fig8.add_trace(go.Bar(
            x=df['Ngày'], y=df['Linehaul Late'],
            marker=dict(color='#f43f5e', line=dict(color='#9f1239', width=1)),
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Linehaul Late']],
            textposition='outside',
            textfont=dict(size=14, color='#9f1239', family="JetBrains Mono"),
        ))
        fig8 = clean_layout(fig8, "Linehaul Late | 干线延迟", height=380)
        fig8.update_layout(showlegend=False)
        st.plotly_chart(fig8, use_container_width=True, key=f"{hub_name}_{period_label}_fig8")

    with col_l3:
        fig9 = go.Figure()
        fig9.add_trace(go.Bar(
            x=df['Ngày'], y=df['Backlog'], name="Total",
            marker=dict(color='#fcd34d', line=dict(color='#b45309', width=1)),
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['Backlog']],
            textposition='outside',
            textfont=dict(size=14, color='#b45309', family="JetBrains Mono"),
        ))
        fig9.add_trace(go.Bar(
            x=df['Ngày'], y=df['Backlog 24H'], name=">24H",
            marker=dict(color='#ef4444', line=dict(color='#991b1b', width=1)),
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['Backlog 24H']],
            textposition='outside',
            textfont=dict(size=13, color='#991b1b', family="JetBrains Mono"),
        ))
        fig9 = clean_layout(fig9, "Backlog & >24H | 积压", height=380)
        fig9.update_layout(barmode='group', showlegend=True, 
                           legend=dict(x=0, y=1.1, orientation="h"))
        st.plotly_chart(fig9, use_container_width=True, key=f"{hub_name}_{period_label}_fig9")

    # ── Raw data toggle ──
    if show_raw_data:
        show_table = st.checkbox("Xem du lieu chi tiet | 详细数据", key=f"raw_{hub_name}_{period_label}")
        if show_table:
            raw = df.copy()
            for c in raw.columns:
                if c != "Ngày":
                    def _fmt(x, p="%" in c):
                        if pd.isna(x) or str(x).strip() == "": return ""
                        try:
                            return f"{float(x):.1f}%" if p else fmt_vn(float(x))
                        except:
                            return str(x)
                    raw[c] = raw[c].apply(lambda x: _fmt(x))
            st.dataframe(
                raw.set_index("Ngày").T,
                use_container_width=True,
            )

# ════════════════════════════════════════════════════════════
# 6. APP ENTRY
# ════════════════════════════════════════════════════════════
from datetime import datetime
now_str = datetime.now().strftime("%d/%m/%Y · %H:%M")

st.markdown(f"""
<div class="dashboard-header">
    <div class="header-title">J&amp;T Cargo · KPI Dashboard</div>
    <p class="header-subtitle">
        Tổng hợp hiệu suất vận hành · 运营绩效汇总 &nbsp;|&nbsp;
        HCM · Bắc Ninh · SH DC &nbsp;|&nbsp;
        <span style="font-family:'JetBrains Mono',monospace">{now_str}</span>
    </p>
</div>
""", unsafe_allow_html=True)

# ── Load data ──
data_hcm, data_bn, data_sh = get_data()
df_hcm, sum_hcm = data_hcm
df_bn,  sum_bn  = data_bn
df_sh,  sum_sh  = data_sh

if df_hcm.empty and df_bn.empty and df_sh.empty:
    st.warning("⏳ Đang tải dữ liệu… Vui lòng xem thông báo lỗi ở trên.")
    st.stop()

# ── Tabs ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Hồ Chí Minh",
    "Bắc Ninh",
    "SH DC",
    "HCM · 7 Ngày",
    "BN · 7 Ngày",
    "SH DC · 7 Ngày",
])

with tab1:
    render_dashboard(df_hcm, sum_hcm, "#1a56db", "HCM",
                     period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=True)
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669", "Bắc Ninh",
                     period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=True)
with tab3:
    render_dashboard(df_sh, sum_sh, "#7c3aed", "SH DC",
                     period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=True)
with tab4:
    render_dashboard(get_last_7_days(df_hcm), sum_hcm, "#1a56db", "HCM",
                     period_label="7 Ngày", show_weekly=False, num_daily_cols=7, show_raw_data=False)
with tab5:
    render_dashboard(get_last_7_days(df_bn), sum_bn, "#059669", "Bắc Ninh",
                     period_label="7 Ngày", show_weekly=False, num_daily_cols=7, show_raw_data=False)
with tab6:
    render_dashboard(get_last_7_days(df_sh), sum_sh, "#7c3aed", "SH DC",
                     period_label="7 Ngày", show_weekly=False, num_daily_cols=7, show_raw_data=False)
