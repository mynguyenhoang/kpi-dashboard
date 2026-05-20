import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# ════════════════════════════════════════════════════════════
# 1. CẤU HÌNH TRANG & CSS NÂNG CẤP CHUYÊN NGHIỆP
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="J&T Cargo · KPI Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">

<style>
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
    --font:       'Plus Jakarta Sans', sans-serif;
    --font-mono:  'JetBrains Mono', monospace;
}

/* ─── APP BACKGROUND ───────────────────────────────────── */
.stApp, [data-testid="stAppViewContainer"] {
    background: var(--surface-2) !important;
    font-family: var(--font) !important;
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
.header-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,255,255,.15);
    border: 1px solid rgba(255,255,255,.25);
    border-radius: 999px;
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 600;
    color: rgba(255,255,255,.9);
    letter-spacing: .5px;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.header-title {
    font-size: 38px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.5px;
    margin: 0 0 6px;
    line-height: 1.15;
}
.header-subtitle {
    font-size: 15px;
    color: rgba(255,255,255,.65);
    font-weight: 500;
    margin: 0;
}
.header-live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #05c168;
    box-shadow: 0 0 0 3px rgba(5,193,104,.25);
    animation: pulse 2s infinite;
    margin-right: 4px;
}
@keyframes pulse {
    0%,100% { box-shadow: 0 0 0 3px rgba(5,193,104,.25); }
    50%      { box-shadow: 0 0 0 6px rgba(5,193,104,.08); }
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
    padding: 10px 22px !important;
    font-family: var(--font) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all .2s ease !important;
}
button[data-baseweb="tab"] div {
    color: var(--text-muted) !important;
    font-weight: 600 !important;
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
    font-family: var(--font) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    letter-spacing: .4px !important;
    text-transform: uppercase !important;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 28px !important;
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
.section-header-icon {
    width: 36px; height: 36px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.section-header-text {
    font-size: 19px;
    font-weight: 800;
    color: var(--navy);
    letter-spacing: -.3px;
}
.section-header-sub {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-muted);
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
    color: rgba(255,255,255,.85) !important;
    padding: 14px 12px;
    text-align: center;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: .6px;
    text-transform: uppercase;
    border: none !important;
    white-space: nowrap;
}
.kpi-table th:first-child { text-align: left; border-radius: 0; }
.kpi-table tbody tr { transition: background .15s; }
.kpi-table tbody tr:hover { background: #f0f5ff; }
.kpi-table td {
    padding: 12px 12px;
    border-bottom: 1px solid var(--border);
    border-right: none;
    font-size: 14px;
    color: var(--text-main);
    vertical-align: middle;
}
.kpi-table tbody tr:last-child td { border-bottom: none; }

/* Pillar cells */
.col-pillar {
    font-weight: 800 !important;
    font-size: 13px !important;
    text-align: center !important;
    background: var(--surface-2) !important;
    color: var(--navy) !important;
    letter-spacing: .3px;
    border-right: 1px solid var(--border) !important;
    white-space: nowrap;
}
/* Metric name */
.col-metric {
    font-weight: 600 !important;
    color: #1e293b !important;
    font-size: 13.5px !important;
    border-right: 1px solid var(--border) !important;
    min-width: 220px;
}
/* Numbers */
.col-num {
    text-align: right !important;
    font-family: var(--font-mono) !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
    white-space: nowrap;
}
/* MTD highlight */
.col-mtd {
    text-align: right !important;
    font-family: var(--font-mono) !important;
    font-size: 16px !important;
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

/* ─── STALE CHART ───────────────────────────────────────── */
.js-plotly-plot { border-radius: var(--radius); overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU (giữ nguyên logic)
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
    if len(vals) < 81:
        st.error(f"🔴 File chỉ có {len(vals)} dòng, cần ít nhất 81.")
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

        def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx,
                             ms_idx, ms_rt_idx, bl_idx, shc_idx, sht_idx, lhc_idx, lht_idx,
                             cot_total_idx, cot_ontime_idx,
                             cot_total_1am_idx, cot_ontime_1am_idx, cot_rate_1am_idx):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
            data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
            data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
            data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
            data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
            data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
            data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
            data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
            data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
            data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]

            data["COT Total"] = [clean_val(cot_total_idx, c) for c in cols_to_scan]
            data["COT Ontime"] = [clean_val(cot_ontime_idx, c) for c in cols_to_scan]
            data["COT Rate (%)"] = [
                (o / t * 100) if (t and t > 0) else np.nan
                for t, o in zip(data["COT Total"], data["COT Ontime"])
            ]

            data["COT 1AM Total"] = [clean_val(cot_total_1am_idx, c) for c in cols_to_scan]
            data["COT 1AM Ontime"] = [clean_val(cot_ontime_1am_idx, c) for c in cols_to_scan]
            data["COT 1AM Rate (%)"] = [
                val if pd.notna(val) else ((o / t * 100) if (t and t > 0) else np.nan)
                for t, o, val in zip(
                    data["COT 1AM Total"], data["COT 1AM Ontime"],
                    [clean_val(cot_rate_1am_idx, c) for c in cols_to_scan]
                )
            ]

            data["Shuttle Chuyến"] = [clean_val(shc_idx, c) for c in cols_to_scan]
            data["Linehaul Chuyến"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
            data["Shuttle Late"] = [clean_val(sht_idx, c) for c in cols_to_scan]
            data["Linehaul Late"] = [clean_val(lht_idx, c) for c in cols_to_scan]

            data["LH Rate (%)"] = [
                (c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan
                for c, t in zip(data["Linehaul Chuyến"], data["Linehaul Late"])
            ]
            data["SH Rate (%)"] = [
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
                "cw_vin": clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_vin": clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_vout": clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_vout": clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_tproc_wgt": clean_val(tproc_wgt_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_tproc_wgt": clean_val(tproc_wgt_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_ms": clean_val(ms_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_ms": clean_val(ms_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_bl": clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_bl": clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_cot_ontime": clean_val(cot_ontime_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_cot_ontime": clean_val(cot_ontime_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_lhot": lhot(cw_idx), "pw_lhot": lhot(pw_idx),
                "cw_shot": shot(cw_idx), "pw_shot": shot(pw_idx),
                "cw_cot": get_rate(cot_ontime_idx, cot_total_idx, cw_idx),
                "pw_cot": get_rate(cot_ontime_idx, cot_total_idx, pw_idx),
            }
            return pd.DataFrame(data), weekly_summary

        data_hcm = extract_hub_data(
            vin_idx=4, vout_idx=5, win_idx=6, wout_idx=7, tproc_vol_idx=8, tproc_wgt_idx=9,
            ms_idx=23, ms_rt_idx=24, bl_idx=42,
            cot_total_idx=47, cot_ontime_idx=48,
            cot_total_1am_idx=50, cot_ontime_1am_idx=51, cot_rate_1am_idx=52,
            shc_idx=53, lhc_idx=54, sht_idx=55, lht_idx=56
        )
        data_bn = extract_hub_data(
            vin_idx=10, vout_idx=11, win_idx=12, wout_idx=13, tproc_vol_idx=14, tproc_wgt_idx=15,
            ms_idx=25, ms_rt_idx=26, bl_idx=43,
            cot_total_idx=59, cot_ontime_idx=60,
            cot_total_1am_idx=62, cot_ontime_1am_idx=63, cot_rate_1am_idx=64,
            shc_idx=65, lhc_idx=66, sht_idx=67, lht_idx=68
        )
        data_sh = extract_hub_data(
            vin_idx=16, vout_idx=17, win_idx=18, wout_idx=19, tproc_vol_idx=20, tproc_wgt_idx=21,
            ms_idx=27, ms_rt_idx=28, bl_idx=44,
            cot_total_idx=71, cot_ontime_idx=72,
            cot_total_1am_idx=74, cot_ontime_1am_idx=75, cot_rate_1am_idx=76,
            shc_idx=77, lhc_idx=78, sht_idx=79, lht_idx=80
        )
        return data_hcm, data_bn, data_sh

    except Exception as e:
        st.error(f"🔴 Lỗi xử lý dữ liệu: {str(e)}")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})


# ════════════════════════════════════════════════════════════
# 3. TIỆN ÍCH ĐỊNH DẠNG
# ════════════════════════════════════════════════════════════
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
        return f"<td style='text-align:center;color:#94a3b8;font-size:13px'>—</td><td class='col-num'>{cur_str}</td><td class='col-num'>—</td>"
    if pd.isna(cur):
        prev_str = f"{prev:.2f}%" if is_pct else fmt_vn(prev)
        return f"<td style='text-align:center;color:#94a3b8;font-size:13px'>—</td><td class='col-num'>—</td><td class='col-num'>{prev_str}</td>"

    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)

    is_positive = diff > 0
    good = (is_positive and not inverse) or (not is_positive and inverse)

    if diff > 0:
        bg = "#ecfdf5" if good else "#fef2f2"
        tc = "#065f46" if good else "#b91c1c"
        sign = "+"
        arrow = "▲"
    elif diff < 0:
        bg = "#fef2f2" if good else "#ecfdf5"
        tc = "#b91c1c" if good else "#065f46"
        sign = ""
        arrow = "▼"
    else:
        bg = "#f8fafc"; tc = "#64748b"; sign = ""; arrow = "●"

    wow_str = f"{arrow} {sign}{pct:.1f}%" if not is_pct else f"{arrow} {sign}{diff:.1f}%"
    cur_str = fmt_vn(cur) if not is_pct else f"{cur:.2f}%"
    prev_str = fmt_vn(prev) if not is_pct else f"{prev:.2f}%"

    return (
        f"<td style='background:{bg};color:{tc};font-weight:800;text-align:center;"
        f"font-size:13px;border-radius:6px;white-space:nowrap'>{wow_str}</td>"
        f"<td class='col-num'>{cur_str}</td>"
        f"<td class='col-num'>{prev_str}</td>"
    )


# ════════════════════════════════════════════════════════════
# 4. CHART THEME
# ════════════════════════════════════════════════════════════
CHART_FONT = dict(family="Plus Jakarta Sans, sans-serif", size=13, color="#0b1437")

def clean_layout(fig, title, height=480):
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family="Plus Jakarta Sans, sans-serif", size=18, color="#0b1437", weight="bold"),
            x=0, xanchor='left', pad=dict(l=4, t=4)
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=56, b=28, l=8, r=8),
        height=height,
        font=CHART_FONT,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#5a6585"),
            tickangle=-45,
            linecolor="#e8edf9",
            showline=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f0f4ff",
            gridwidth=1,
            tickfont=dict(size=12, color="#5a6585"),
            zeroline=False,
        ),
        hoverlabel=dict(
            font=dict(family="Plus Jakarta Sans, sans-serif", size=14),
            bgcolor="white",
            bordercolor="#e8edf9",
        ),
        legend=dict(
            font=dict(family="Plus Jakarta Sans, sans-serif", size=13),
            bgcolor="rgba(255,255,255,.9)",
            bordercolor="#e8edf9",
            borderwidth=1,
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
    last_idx = valid_df.index[-1]
    start_idx = max(0, last_idx - 6)
    return df.iloc[start_idx:last_idx+1].reset_index(drop=True)


def render_dashboard(df, summary, accent_color, hub_name, period_label="MTD",
                     show_weekly=True, num_daily_cols=3, show_raw_data=False):
    if df.empty: return

    # ── valid slice ──
    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    actual_cols = min(len(valid_df), num_daily_cols)
    data_slice = valid_df.tail(actual_cols + 1).reset_index(drop=True)

    if len(data_slice) > actual_cols:
        d_names = data_slice['Ngày'].tolist()[1:]
    else:
        d_names = data_slice['Ngày'].tolist()

    pad_len = num_daily_cols - len(d_names)
    d_display = ["-"] * pad_len + d_names

    # ── daily delta cells ──
    def get_d(col_name, is_pct=False, inverse=False):
        vals_list = data_slice[col_name].tolist()
        if len(vals_list) > actual_cols:
            cur_vals = vals_list[1:]
            prev_vals = vals_list[:-1]
        else:
            cur_vals = vals_list
            prev_vals = [np.nan] + vals_list[:-1]

        cur_vals = [np.nan] * pad_len + cur_vals
        prev_vals = [np.nan] * pad_len + prev_vals

        cells = []
        for i in range(num_daily_cols):
            cur = cur_vals[i]
            prev = prev_vals[i]
            if pd.isna(cur):
                cells.append("<td class='col-num' style='color:#cbd5e1'>—</td>")
                continue
            cur_str = f"{cur:.1f}%" if is_pct else fmt_vn(cur)
            if pd.notna(prev):
                diff = cur - prev
                if diff < 0:
                    color = "#065f46" if inverse else "#dc2626"
                    icon = "↓"
                elif diff > 0:
                    color = "#dc2626" if inverse else "#065f46"
                    icon = "↑"
                else:
                    color = "#94a3b8"; icon = ""
                styled = (
                    f"<span style='color:{color};font-family:var(--font-mono);"
                    f"font-size:14px;font-weight:700'>{cur_str}"
                    f"<sup style='font-size:10px;margin-left:2px'>{icon}</sup></span>"
                )
            else:
                styled = f"<span style='font-family:var(--font-mono);font-size:14px;font-weight:700;color:var(--navy)'>{cur_str}</span>"

            bg = "#f8fafc" if i % 2 == 0 else "white"
            cells.append(f"<td class='col-num' style='background:{bg}'>{styled}</td>")
        return "".join(cells)

    # ── MTD aggregates ──
    t_vin        = df['Inbound Vol'].sum(skipna=True)
    t_vout       = df['Outbound Vol'].sum(skipna=True)
    t_tproc_vol  = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt  = df['Total Process Wgt'].sum(skipna=True)
    t_ms         = df['Missort'].sum(skipna=True)
    t_bl         = df['Backlog'].sum(skipna=True)
    cot_ontime_mtd = df['COT Ontime'].sum(skipna=True)

    lh_tot   = df['Linehaul Chuyến'].fillna(0).sum()
    lh_late  = df['Linehaul Late'].fillna(0).sum()
    lhot_mtd = (lh_tot - lh_late) / lh_tot * 100 if lh_tot > 0 else 0
    sh_tot   = df['Shuttle Chuyến'].fillna(0).sum()
    sh_late  = df['Shuttle Late'].fillna(0).sum()
    shot_mtd = (sh_tot - sh_late) / sh_tot * 100 if sh_tot > 0 else 0
    cot_mtd  = df['COT Ontime'].sum() / df['COT Total'].sum() * 100 if df['COT Total'].sum() > 0 else 0

    # ── 6 summary cards ──
    CARDS = [
        ("📦", "Inbound", "入库", t_vin, period_label, "#1a56db"),
        ("📤", "Outbound", "出库", t_vout, period_label, "#059669"),
        ("🔄", "Tổng đơn xử lý", "总处理量", t_tproc_vol, period_label, "#7c3aed"),
        ("⚖️", "Trọng lượng (kg)", "重量", t_tproc_wgt, period_label, "#0284c7"),
        ("⚠️", "Missort", "错分", t_ms, period_label, "#f59e0b"),
        ("📊", "Backlog", "积压", t_bl, period_label, "#ef4444"),
    ]

    # render as custom metric cards
    cols = st.columns(6)
    for col_obj, (icon, vn, cn, val, lbl, color) in zip(cols, CARDS):
        with col_obj:
            st.markdown(f"""
            <div style="
                background:white;
                border:1px solid #e8edf9;
                border-top:3px solid {color};
                border-radius:14px;
                padding:18px 16px 14px;
                box-shadow:0 2px 8px rgba(11,20,55,.07);
                transition: box-shadow .2s;
            ">
                <div style="font-size:11px;font-weight:700;color:#8896b3;
                    text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">
                    {icon} {vn} · {cn} <span style="background:{color}22;color:{color};
                    padding:2px 7px;border-radius:99px;font-size:10px;margin-left:4px">{lbl}</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:26px;
                    font-weight:700;color:#0b1437;letter-spacing:-1px;line-height:1">
                    {fmt_vn(val)}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI table ──
    header_wow = (
        '<th style="min-width:100px">WOW</th>'
        '<th>Tuần này</th><th>Tuần trước</th>'
    ) if show_weekly else ""
    daily_hdrs = "".join(
        [f"<th style='background:rgba(255,255,255,.12);min-width:90px'>{d}</th>" for d in d_display]
    )

    def build_row(kpi_title, rowspan, kpi_color, metric_name,
                  wow_cur, wow_prev, mtd_val, col_name,
                  is_pct=False, inverse=False, is_first=False):
        kpi_td = (
            f'<td rowspan="{rowspan}" class="col-pillar" '
            f'style="border-left:3px solid {kpi_color};color:{kpi_color};font-size:12px">'
            f'{kpi_title}</td>'
        ) if is_first else ''
        wow_td = get_wow_cell(wow_cur, wow_prev, is_pct, inverse) if show_weekly else ''
        mtd_str = f"{mtd_val:.1f}%" if is_pct else fmt_vn(mtd_val)
        d_tds = get_d(col_name, is_pct, inverse)
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
                  "Missort (đơn) | 错分单量",
                  summary['cw_ms'], summary['pw_ms'], t_ms, 'Missort', inverse=True, is_first=True),
        build_row("", 0, "", "Backlog (đơn) | 积压单量",
                  summary['cw_bl'], summary['pw_bl'], t_bl, 'Backlog', inverse=True),
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

    st.markdown(f"""
    <div class="kpi-wrap">
        <table class="kpi-table">
            <thead><tr>
                <th style="text-align:left;width:90px">KPI</th>
                <th style="text-align:left">Hạng mục | 指标名称</th>
                {header_wow}
                <th style="min-width:110px">{period_label} | 累计</th>
                {daily_hdrs}
            </tr></thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════
    # SECTION 1 · SẢN LƯỢNG
    # ══════════════════════════
    st.markdown(f"""
    <div class="section-header">
        <div class="section-header-icon" style="background:{accent_color}18">
            <span>📈</span>
        </div>
        <div>
            <div class="section-header-text">Sản Lượng & Năng Suất · 生产与产能</div>
            <div class="section-header-sub">Inbound / Outbound / Trọng lượng hàng ngày</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1, 1])

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Ngày'], y=df['Inbound Vol'], name="Inbound",
            fill='tozeroy', mode='lines+markers',
            line=dict(color='#1a56db', width=3),
            marker=dict(size=5, color='#1a56db'),
            fillcolor='rgba(26,86,219,.08)',
        ))
        fig.add_trace(go.Scatter(
            x=df['Ngày'], y=df['Outbound Vol'], name="Outbound",
            mode='lines+markers',
            line=dict(color='#f59e0b', width=3, dash='dot'),
            marker=dict(size=5, color='#f59e0b'),
        ))
        fig = clean_layout(fig, "Inbound & Outbound | 每日入库/出库")
        fig.update_layout(legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True)

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
            textfont=dict(size=12, color='white', family="JetBrains Mono"),
        ))
        fig2 = clean_layout(fig2, "Năng suất (Số đơn) | 产能单数")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

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
            textfont=dict(size=12, color='white', family="JetBrains Mono"),
        ))
        fig3 = clean_layout(fig3, "Năng suất (Kg) | 产能重量")
        fig3.update_layout(showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # ══════════════════════════
    # SECTION 2 · VẬN TẢI & COT
    # ══════════════════════════
    st.markdown(f"""
    <div class="section-header">
        <div class="section-header-icon" style="background:{accent_color}18">
            <span>🚚</span>
        </div>
        <div>
            <div class="section-header-text">Vận Tải & COT · 运输与准时出库管理</div>
            <div class="section-header-sub">Linehaul / Shuttle / Sent Volume Ontime</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_t1, col_t2, col_t3 = st.columns(3)

    with col_t1:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=df['Ngày'], y=df['Shuttle Chuyến'], name="Shuttle",
            marker_color='#3b82f6',
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Shuttle Chuyến']],
            textposition='inside', textfont=dict(size=12, color='white', weight='bold'),
        ))
        fig4.add_trace(go.Bar(
            x=df['Ngày'], y=df['Linehaul Chuyến'], name="Linehaul",
            marker_color='#f97316',
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Linehaul Chuyến']],
            textposition='inside', textfont=dict(size=12, color='white', weight='bold'),
        ))
        fig4 = clean_layout(fig4, "Số chuyến Shuttle/LH | 总车次")
        fig4.update_layout(barmode='stack', legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig4, use_container_width=True)

    with col_t2:
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=df['Ngày'], y=df['COT Total'], name="Tổng đơn",
            marker_color='#bfdbfe', opacity=0.7,
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['COT Ontime']],
            textposition='inside', textangle=-90, insidetextanchor='end',
            textfont=dict(size=11, color='#1e3a8a'),
        ))
        fig5.add_trace(go.Scatter(
            x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ %",
            yaxis="y2",
            line=dict(color='#059669', width=3),
            mode='lines+markers+text',
            marker=dict(size=6, color='#059669'),
            text=[f"{v:.0f}%" if pd.notna(v) and v > 0 else "" for v in df['COT Rate (%)']],
            textposition="top center",
            textfont=dict(size=13, color='#065f46', family="JetBrains Mono"),
        ))
        fig5 = clean_layout(fig5, "% Sent Volume Ontime | 准时出库率")
        fig5.update_layout(
            showlegend=False,
            yaxis2=dict(overlaying='y', side='right', range=[0, 115],
                        showgrid=False, tickfont=dict(size=12, color='#059669'))
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col_t3:
        fig6 = go.Figure()
        fig6.add_trace(go.Bar(
            x=df['Ngày'], y=df['COT 1AM Total'], name="Tổng 1AM",
            marker_color='#fed7aa', opacity=0.7,
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['COT 1AM Ontime']],
            textposition='inside', textangle=-90, insidetextanchor='end',
            textfont=dict(size=11, color='#7c2d12'),
        ))
        fig6.add_trace(go.Scatter(
            x=df['Ngày'], y=df['COT 1AM Rate (%)'], name="Tỷ lệ 1AM",
            yaxis="y2",
            line=dict(color='#ea580c', width=3),
            mode='lines+markers+text',
            marker=dict(size=6, color='#ea580c'),
            text=[f"{v:.0f}%" if pd.notna(v) and v > 0 else "" for v in df['COT 1AM Rate (%)']],
            textposition="top center",
            textfont=dict(size=13, color='#7c2d12', family="JetBrains Mono"),
        ))
        fig6 = clean_layout(fig6, "% Sent Volume 1AM | 1AM准时率")
        fig6.update_layout(
            showlegend=False,
            yaxis2=dict(overlaying='y', side='right', range=[0, 115],
                        showgrid=False, tickfont=dict(size=12, color='#ea580c'))
        )
        st.plotly_chart(fig6, use_container_width=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1, 1.2])

    with col_l1:
        fig7 = go.Figure()
        fig7.add_trace(go.Bar(
            x=df['Ngày'], y=df['Shuttle Late'],
            marker=dict(color='#ef4444',
                        line=dict(color='#b91c1c', width=1)),
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Shuttle Late']],
            textposition='outside',
            textfont=dict(size=13, color='#b91c1c', family="JetBrains Mono"),
        ))
        fig7 = clean_layout(fig7, "Shuttle Late | 支线延迟", height=380)
        fig7.update_layout(showlegend=False)
        st.plotly_chart(fig7, use_container_width=True)

    with col_l2:
        fig8 = go.Figure()
        fig8.add_trace(go.Bar(
            x=df['Ngày'], y=df['Linehaul Late'],
            marker=dict(color='#f43f5e',
                        line=dict(color='#9f1239', width=1)),
            text=[int(x) if pd.notna(x) and x > 0 else "" for x in df['Linehaul Late']],
            textposition='outside',
            textfont=dict(size=13, color='#9f1239', family="JetBrains Mono"),
        ))
        fig8 = clean_layout(fig8, "Linehaul Late | 干线延迟", height=380)
        fig8.update_layout(showlegend=False)
        st.plotly_chart(fig8, use_container_width=True)

    with col_l3:
        fig9 = go.Figure()
        fig9.add_trace(go.Bar(
            x=df['Ngày'], y=df['Backlog'],
            marker=dict(
                color=df['Backlog'],
                colorscale=[[0, '#fde68a'], [1, '#f59e0b']],
                showscale=False,
                line=dict(color='#b45309', width=1),
            ),
            text=[fmt_vn(x) if pd.notna(x) and x > 0 else "" for x in df['Backlog']],
            textposition='outside',
            textfont=dict(size=13, color='#b45309', family="JetBrains Mono"),
        ))
        fig9 = clean_layout(fig9, "Backlog | 积压", height=380)
        fig9.update_layout(showlegend=False)
        st.plotly_chart(fig9, use_container_width=True)

    # ── Raw data expander ──
    if show_raw_data:
        with st.expander("🔍 Dữ liệu chi tiết | 详细数据"):
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
            st.dataframe(raw.set_index("Ngày").T, use_container_width=True)


# ════════════════════════════════════════════════════════════
# 6. APP ENTRY
# ════════════════════════════════════════════════════════════

# ── Header banner ──
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
    "🏙️  Hồ Chí Minh",
    "🏭  Bắc Ninh",
    "🏢  SH DC",
    "📅  HCM · 7 Ngày",
    "📅  BN · 7 Ngày",
    "📅  SH DC · 7 Ngày",
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
