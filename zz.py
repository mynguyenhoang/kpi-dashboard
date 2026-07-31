import streamlit.components.v1 as components
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime

# ════════════════════════════════════════════════════════════
# 1. CẤU HÌNH TRANG & CSS (STYLE POWER BI TỐI GIẢN & CHUYÊN NGHIỆP)
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="J&T Cargo KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sử dụng font Segoe UI (chuẩn Microsoft/Power BI) hoặc Roboto
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ─── RESET & BASE ─────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
:root {
    --bg-main:    #F3F2F1; /* Xám nhạt chuẩn Power BI */
    --surface:    #FFFFFF;
    --border:     #E1DFDD;
    --text-main:  #323130;
    --text-muted: #605E5C;
    --primary:    #0078D4; /* Xanh Microsoft */
    --green:      #107C10;
    --red:        #D13438;
    --shadow-sm:  0 1.6px 3.6px 0 rgba(0,0,0,0.132), 0 0.3px 0.9px 0 rgba(0,0,0,0.108);
    --radius:     4px; /* Bo góc cực nhỏ, nam tính và chuyên nghiệp */
    --font:       'Inter', 'Segoe UI', sans-serif;
    --font-mono:  'JetBrains Mono', monospace;
}

/* ─── APP BACKGROUND ───────────────────────────────────── */
.stApp, [data-testid="stAppViewContainer"] {
    background: var(--bg-main) !important;
    font-family: var(--font) !important;
}
body, p, div, span, td, th, label, input, button {
    font-family: var(--font) !important;
    color: var(--text-main);
}

/* ─── HIDE STREAMLIT CHROME ────────────────────────────── */
#MainMenu, header, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stHeader"] {
    visibility: hidden !important;
    height: 0 !important;
}

/* ─── MAIN HEADER BANNER ───────────────────────────────── */
.dashboard-header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 20px 32px;
    margin-bottom: 24px;
    box-shadow: var(--shadow-sm);
    border-radius: var(--radius);
}
.header-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-main);
    margin: 0 0 4px;
    line-height: 1.2;
}
.header-subtitle {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
}

/* ─── TABS ─────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 20px !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 0 !important;
    margin-bottom: 20px !important;
}
button[data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 10px 4px !important;
    font-family: var(--font) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    color: var(--text-muted) !important;
    border-bottom: 3px solid transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--primary) !important;
    border-bottom: 3px solid var(--primary) !important;
}

/* ─── SECTION HEADERS ──────────────────────────────────── */
.section-header {
    margin: 32px 0 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
.section-header-text {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-main);
}
.section-header-sub {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
}

/* ─── EXPANDER FIX ──────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
    margin-top: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU (GIỮ NGUYÊN LOGIC)
# ════════════════════════════════════════════════════════════
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except Exception as e:
        st.error(f"Lỗi lấy Token Feishu: {str(e)}")
        return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token API Feishu.")
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
                    st.error("API Feishu báo 'Not ready' quá lâu.")
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else:
                st.error(f"Lỗi từ Feishu API: {res.get('msg')}")
                return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception as e:
            st.error(f"Lỗi kết nối: {str(e)}")
            return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not res_data:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals:
        st.error("File Feishu trống!")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if len(vals) < 80:
        st.error(f"File chỉ có {len(vals)} dòng, cần ít nhất 80.")
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
            bl_idx, bl_24h_idx, cot_total_idx, cot_ontime_idx,
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
                "cw_win":       clean_val(win_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_win":       clean_val(win_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_wout":      clean_val(wout_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_wout":      clean_val(wout_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_tproc_wgt": clean_val(tproc_wgt_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_tproc_wgt": clean_val(tproc_wgt_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_bl":        clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_bl":        clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_bl_24h":    clean_val(bl_24h_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_bl_24h":    clean_val(bl_24h_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_cot_ontime": clean_val(cot_ontime_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_cot_ontime": clean_val(cot_ontime_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_cot_1am_ontime": clean_val(cot_ontime_1am_idx, cw_idx) if cw_idx != -1 else 0,
                "pw_cot_1am_ontime": clean_val(cot_ontime_1am_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_lhot": lhot(cw_idx), "pw_lhot": lhot(pw_idx),
                "cw_shot": shot(cw_idx), "pw_shot": shot(pw_idx),
                "cw_cot": get_rate(cot_ontime_idx, cot_total_idx, cw_idx),
                "pw_cot": get_rate(cot_ontime_idx, cot_total_idx, pw_idx),
                "cw_cot_1am": get_rate(cot_ontime_1am_idx, cot_total_1am_idx, cw_idx),
                "pw_cot_1am": get_rate(cot_ontime_1am_idx, cot_total_1am_idx, pw_idx),
            }
            return pd.DataFrame(data), weekly_summary

        data_hcm = extract_hub_data(
            vin_idx=4,  vout_idx=5,  win_idx=6,  wout_idx=7,
            tproc_vol_idx=8,  tproc_wgt_idx=9, bl_idx=35, bl_24h_idx=36,
            cot_total_idx=46,    cot_ontime_idx=47,
            cot_total_1am_idx=49, cot_ontime_1am_idx=50, cot_rate_1am_idx=51,
            shc_idx=52, lhc_idx=53, sht_idx=54, lht_idx=55,
        )
        data_bn = extract_hub_data(
            vin_idx=10, vout_idx=11, win_idx=12, wout_idx=13,
            tproc_vol_idx=14, tproc_wgt_idx=15, bl_idx=38, bl_24h_idx=39,
            cot_total_idx=58,    cot_ontime_idx=59,
            cot_total_1am_idx=61, cot_ontime_1am_idx=62, cot_rate_1am_idx=63,
            shc_idx=64, lhc_idx=65, sht_idx=66, lht_idx=67,
        )
        data_sh = extract_hub_data(
            vin_idx=16, vout_idx=17, win_idx=18, wout_idx=19,
            tproc_vol_idx=20, tproc_wgt_idx=21, bl_idx=41, bl_24h_idx=42,
            cot_total_idx=70,    cot_ontime_idx=71,
            cot_total_1am_idx=73, cot_ontime_1am_idx=74, cot_rate_1am_idx=75,
            shc_idx=76, lhc_idx=77, sht_idx=78, lht_idx=79,
        )
        return data_hcm, data_bn, data_sh

    except Exception as e:
        st.error(f"Lỗi xử lý dữ liệu: {str(e)}")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

# ════════════════════════════════════════════════════════════
# 3. TIỆN ÍCH ĐỊNH DẠNG (STYLE BẢNG MATRIX POWER BI)
# ════════════════════════════════════════════════════════════
_IFRAME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{background:transparent;font-family:'Inter',sans-serif;font-size:13px;color:#323130;}
.kpi-wrap{background:#fff;border:1px solid #E1DFDD;border-radius:4px;overflow:hidden;}
.kpi-table{width:100%;border-collapse:collapse;font-family:'Inter',sans-serif}
.kpi-table thead tr{background:#F3F2F1;border-bottom:2px solid #C8C6C4;}
.kpi-table th{color:#323130;padding:12px 14px;text-align:center;font-size:12px;font-weight:600;border:none;white-space:nowrap;border-right:1px solid #E1DFDD;}
.kpi-table th:first-child{text-align:left}
.kpi-table tbody tr{border-bottom:1px solid #EDEBE9;}
.kpi-table tbody tr:nth-child(even){background:#FAFAFA;}
.kpi-table tbody tr:hover{background:#F3F2F1;}
.kpi-table td{padding:10px 14px;font-size:13px;vertical-align:middle;border-right:1px solid #E1DFDD;}
.kpi-table tbody tr:last-child td{border-bottom:none}
.col-pillar{font-weight:600;font-size:12px;text-align:left;background:#FFFFFF;white-space:nowrap;}
.col-metric{font-weight:500;color:#323130;min-width:200px;}
.col-num{text-align:right;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:400;white-space:nowrap}
.col-mtd{text-align:right;font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;background:#F8F8F8;}
.status-good{color:#107C10;}
.status-bad{color:#D13438;}
.status-neutral{color:#605E5C;}
"""

def _html(html_body: str, height: int = 500):
    full = f"<!DOCTYPE html><html><head><style>{_IFRAME_CSS}</style></head><body>{html_body}</body></html>"
    components.html(full, height=height, scrolling=True)

def fmt_vn(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) and pd.isna(prev):
        return "<td class='col-num status-neutral'>—</td><td class='col-num'></td><td class='col-num'></td>"
    if pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct and pd.notna(cur) else fmt_vn(cur)
        if pd.isna(cur): cur_str = "—"
        return f"<td class='col-num status-neutral'>—</td><td class='col-num'>{cur_str}</td><td class='col-num'>—</td>"
    if pd.isna(cur):
        prev_str = f"{prev:.2f}%" if is_pct else fmt_vn(prev)
        return f"<td class='col-num status-neutral'>—</td><td class='col-num'>—</td><td class='col-num'>{prev_str}</td>"

    diff = cur - prev
    pct  = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    is_positive = diff > 0
    good = (is_positive and not inverse) or (not is_positive and inverse)

    status_class = "status-good" if good else "status-bad" if diff != 0 else "status-neutral"
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "-"
    
    wow_str = f"{arrow} {abs(pct):.1f}%" if diff != 0 else "-"
    cur_str  = fmt_vn(cur) if not is_pct else f"{cur:.1f}%"
    prev_str = fmt_vn(prev) if not is_pct else f"{prev:.1f}%"

    return (
        f"<td class='col-num {status_class}'>{wow_str}</td>"
        f"<td class='col-num'>{cur_str}</td>"
        f"<td class='col-num' style='color:#605E5C'>{prev_str}</td>"
    )

# ════════════════════════════════════════════════════════════
# 4. CHART THEME (CHUẨN BÁO CÁO DOANH NGHIỆP)
# ════════════════════════════════════════════════════════════
CHART_FONT = dict(family="Inter, sans-serif", size=12, color="#323130")

def clean_layout(fig, title, height=360):
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family="Inter, sans-serif", size=14, color="#323130", weight="bold"),
            x=0, xanchor='left', pad=dict(l=0, t=10),
            yref='paper', y=1, yanchor='bottom',
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(t=50, b=40, l=10, r=10),
        height=height,
        font=CHART_FONT,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=11, color="#605E5C"),
            tickangle=-45,
            linecolor="#E1DFDD",
            showline=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F3F2F1",
            gridwidth=1,
            tickfont=dict(size=11, color="#605E5C"),
            zeroline=True,
            zerolinecolor="#E1DFDD"
        ),
        hoverlabel=dict(
            font=dict(family="Inter, sans-serif", size=12),
            bgcolor="#FFFFFF",
            bordercolor="#E1DFDD",
        ),
        legend=dict(
            font=dict(family="Inter, sans-serif", size=11),
            orientation="h",
            x=0, y=1.1,
            xanchor="left", yanchor="bottom",
        )
    )
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

def render_dashboard(df, summary, hub_name, period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=False):
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

    # ── Hàm vẽ cell ngày ──
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
                cells.append("<td class='col-num' style='color:#C8C6C4'>—</td>")
                continue

            cur_str = f"{cur:.1f}%" if is_pct else fmt_vn(cur)
            
            if pd.notna(prev) and prev != cur:
                diff     = cur - prev
                going_up = diff > 0
                good     = (going_up and not inverse) or (not going_up and inverse)
                arrow    = "▲" if going_up else "▼"
                status_color = "#107C10" if good else "#D13438"
                
                # Format phẳng, ko background rườm rà
                indicator = f"<span style='color:{status_color}; font-size:11px; margin-left:4px;'>{arrow}</span>"
                cells.append(f"<td class='col-num'>{cur_str}{indicator}</td>")
            else:
                cells.append(f"<td class='col-num'>{cur_str}</td>")
        return "".join(cells)

    # ── MTD aggregates ──
    t_vin          = df['Inbound Vol'].sum(skipna=True)
    t_vout         = df['Outbound Vol'].sum(skipna=True)
    t_tproc_vol    = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt    = df['Total Process Wgt'].sum(skipna=True)
    t_bl           = df['Backlog'].sum(skipna=True)

    # ── KPI Cards (Chuẩn BI: Trắng, Phẳng, Viền xám nhạt) ──
    CARDS = [
        ("Inbound", t_vin, period_label),
        ("Outbound", t_vout, period_label),
        ("Sản lượng xử lý", t_tproc_vol, period_label),
        ("Trọng lượng (kg)", t_tproc_wgt, period_label),
        ("Tồn kho (Backlog)", t_bl, period_label),
    ]
    cols = st.columns(5)
    for col_obj, (title, val, lbl) in zip(cols, CARDS):
        with col_obj:
            st.markdown(f"""
            <div style="
                background:#FFFFFF;
                border:1px solid #E1DFDD;
                border-radius:4px;
                padding:16px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            ">
                <div style="font-size:12px;font-weight:600;color:#605E5C;text-transform:uppercase;margin-bottom:8px;">
                    {title}
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:600;color:#323130;line-height:1">
                    {fmt_vn(val)}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI Matrix Table ──
    header_wow = (
        '<th style="width:70px">WOW</th>'
        '<th style="width:90px">Tuần này</th>'
        '<th style="width:90px">Tuần trước</th>'
    ) if show_weekly else ""

    daily_hdrs = "".join([f"<th>{d}</th>" for d in d_display])

    def build_row(kpi_title, rowspan, metric_name, wow_cur, wow_prev, mtd_val, col_name, is_pct=False, inverse=False, is_first=False):
        kpi_td = f'<td rowspan="{rowspan}" class="col-pillar">{kpi_title}</td>' if is_first else ''
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

    cot_ontime_mtd = df['COT Ontime'].sum(skipna=True)
    cot_1am_mtd    = df['COT 1AM Ontime'].sum() / df['COT 1AM Total'].sum() * 100 if df['COT 1AM Total'].sum() > 0 else 0
    lhot_mtd       = (df['Linehaul Chuyến'].sum() - df['Linehaul Late'].sum()) / df['Linehaul Chuyến'].sum() * 100 if df['Linehaul Chuyến'].sum() > 0 else 0
    cot_mtd        = df['COT Ontime'].sum() / df['COT Total'].sum() * 100 if df['COT Total'].sum() > 0 else 0

    rows = [
        build_row("Sản lượng", 4, "Inbound", summary['cw_vin'], summary['pw_vin'], t_vin, 'Inbound Vol', is_first=True),
        build_row("", 0, "Outbound", summary['cw_vout'], summary['pw_vout'], t_vout, 'Outbound Vol'),
        build_row("", 0, "Trọng lượng Inbound", summary['cw_win'], summary['pw_win'], df['Inbound Wgt'].sum(), 'Inbound Wgt'),
        build_row("", 0, "Trọng lượng Outbound", summary['cw_wout'], summary['pw_wout'], df['Outbound Wgt'].sum(), 'Outbound Wgt'),
        
        build_row("Chất lượng", 6, "Backlog", summary['cw_bl'], summary['pw_bl'], t_bl, 'Backlog', inverse=True, is_first=True),
        build_row("", 0, "Backlog >24H", summary['cw_bl_24h'], summary['pw_bl_24h'], df['Backlog 24H'].sum(), 'Backlog 24H', inverse=True),
        build_row("", 0, "Đơn đúng COT", summary['cw_cot_ontime'], summary['pw_cot_ontime'], cot_ontime_mtd, 'COT Ontime'),
        build_row("", 0, "Tỷ lệ Ontime (%)", summary['cw_cot'], summary['pw_cot'], cot_mtd, 'COT Rate (%)', is_pct=True),
        build_row("", 0, "Đơn đúng 1AM", summary['cw_cot_1am_ontime'], summary['pw_cot_1am_ontime'], df['COT 1AM Ontime'].sum(), 'COT 1AM Ontime'),
        build_row("", 0, "Tỷ lệ 1AM (%)", summary['cw_cot_1am'], summary['pw_cot_1am'], cot_1am_mtd, 'COT 1AM Rate (%)', is_pct=True),
        
        build_row("Vận tải", 2, "Linehaul Ontime (%)", summary['cw_lhot'], summary['pw_lhot'], lhot_mtd, 'LH Rate (%)', is_pct=True, is_first=True),
        build_row("", 0, "Shuttle Ontime (%)", summary['cw_shot'], summary['pw_shot'], (df['Shuttle Chuyến'].sum()-df['Shuttle Late'].sum())/df['Shuttle Chuyến'].sum()*100 if df['Shuttle Chuyến'].sum()>0 else 0, 'SH Rate (%)', is_pct=True),
    ]

    _thead = (
        f'<th style="width:80px">Nhóm</th>'
        f'<th style="text-align:left">Chỉ số</th>'
        f'{header_wow}'
        f'<th style="width:90px">Lũy kế</th>'
        f'{daily_hdrs}'
    )
    _html(f'<div class="kpi-wrap"><table class="kpi-table"><thead><tr>{_thead}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>', height=550 if show_weekly else 500)

    # ══════════════════════════
    # BIỂU ĐỒ (SỬ DỤNG MÀU DOANH NGHIỆP: XANH/XÁM/ĐỎ/CAM)
    # ══════════════════════════
    st.markdown('<div class="section-header"><div class="section-header-text">Sản lượng & Năng suất</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", mode='lines+markers', line=dict(color='#0078D4', width=2), marker=dict(size=5)))
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", mode='lines+markers', line=dict(color='#605E5C', width=2, dash='dot'), marker=dict(size=5)))
        st.plotly_chart(clean_layout(fig1, "Inbound vs Outbound"), use_container_width=True, key=f"{hub_name}_{period_label}_1")

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#0078D4'))
        st.plotly_chart(clean_layout(fig2, "Tổng đơn xử lý"), use_container_width=True, key=f"{hub_name}_{period_label}_2")

    with c3:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#2899F5'))
        st.plotly_chart(clean_layout(fig3, "Tổng trọng lượng (kg)"), use_container_width=True, key=f"{hub_name}_{period_label}_3")

    st.markdown('<div class="section-header"><div class="section-header-text">Vận tải & Tỷ lệ hoàn thành (COT)</div></div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    
    with c4:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Chuyến'], name="Shuttle", marker_color='#A6A6A6'))
        fig4.add_trace(go.Bar(x=df['Ngày'], y=df['Linehaul Chuyến'], name="Linehaul", marker_color='#0078D4'))
        fig4.update_layout(barmode='stack')
        st.plotly_chart(clean_layout(fig4, "Số chuyến xe"), use_container_width=True, key=f"{hub_name}_{period_label}_4")

    with c5:
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(x=df['Ngày'], y=df['COT Total'], name="Tổng đơn", marker_color='#E1DFDD'))
        fig5.add_trace(go.Scatter(x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ (%)", yaxis="y2", line=dict(color='#107C10', width=2), mode='lines+markers'))
        fig5 = clean_layout(fig5, "Tỷ lệ Ontime COT")
        fig5.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False))
        st.plotly_chart(fig5, use_container_width=True, key=f"{hub_name}_{period_label}_5")

    with c6:
        fig9 = go.Figure()
        fig9.add_trace(go.Bar(x=df['Ngày'], y=df['Backlog'], name="Total", marker_color='#FFB900'))
        fig9.add_trace(go.Bar(x=df['Ngày'], y=df['Backlog 24H'], name=">24H", marker_color='#D13438'))
        fig9.update_layout(barmode='group')
        st.plotly_chart(clean_layout(fig9, "Tồn kho (Backlog)"), use_container_width=True, key=f"{hub_name}_{period_label}_9")

    # ── Raw data toggle ──
    if show_raw_data:
        if st.checkbox("Xem dữ liệu bảng chi tiết", key=f"raw_{hub_name}_{period_label}"):
            raw = df.copy()
            for c in raw.columns:
                if c != "Ngày":
                    raw[c] = raw[c].apply(lambda x: f"{float(x):.1f}%" if "%" in c and pd.notna(x) else (fmt_vn(float(x)) if pd.notna(x) else ""))
            st.dataframe(raw.set_index("Ngày").T, use_container_width=True)


# ════════════════════════════════════════════════════════════
# 6. APP ENTRY
# ════════════════════════════════════════════════════════════
now_str = datetime.now().strftime("%d/%m/%Y · %H:%M")

st.markdown(f"""
<div class="dashboard-header">
    <div class="header-title">Hub Operations Dashboard</div>
    <p class="header-subtitle">Báo cáo hiệu suất vận hành | Dữ liệu cập nhật: {now_str}</p>
</div>
""", unsafe_allow_html=True)

# ── Load data ──
df_hcm, sum_hcm = get_data()[0]
df_bn,  sum_bn  = get_data()[1]
df_sh,  sum_sh  = get_data()[2]

if df_hcm.empty and df_bn.empty and df_sh.empty:
    st.stop()

# ── Tabs ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Hồ Chí Minh", "Bắc Ninh", "SH DC", "HCM · 7 Ngày", "BN · 7 Ngày", "SH DC · 7 Ngày"])

with tab1: render_dashboard(df_hcm, sum_hcm, "HCM", "MTD", True, 3, True)
with tab2: render_dashboard(df_bn, sum_bn, "Bắc Ninh", "MTD", True, 3, True)
with tab3: render_dashboard(df_sh, sum_sh, "SH DC", "MTD", True, 3, True)
with tab4: render_dashboard(get_last_7_days(df_hcm), sum_hcm, "HCM", "7 Ngày", False, 7, False)
with tab5: render_dashboard(get_last_7_days(df_bn), sum_bn, "Bắc Ninh", "7 Ngày", False, 7, False)
with tab6: render_dashboard(get_last_7_days(df_sh), sum_sh, "SH DC", "7 Ngày", False, 7, False)
