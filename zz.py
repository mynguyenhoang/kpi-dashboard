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
# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
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

# ─────────────────────────────────────────────────────────────
# MAP INDEX HÀNG (ROW INDEX) THEO SHEET MỚI
# (đã dò lại theo dữ liệu bạn cung cấp — sheet đã chèn thêm khối
#  "Năng suất/FTE" (22-41) nên toàn bộ Backlog/COT/Linehaul bị
#  đẩy lùi xuống so với bản cũ)
# ─────────────────────────────────────────────────────────────
HUB_ROWS = {
    "HCM": dict(
        vin=4, vout=5, win=6, wout=7, tproc_vol=8, tproc_wgt=9,
        fte=24, fte_opm=25, eff_wgt=26, eff_vol=27, eff_wgt_opm=28, eff_vol_opm=29,
        bl=44, bl24=45,
        cot_total=55, cot_ontime=56, cot1am_total=58, cot1am_ontime=59,
        arr24_total=61, arr24_ontime=62,
        shc=64, lhc=65, sht=66, lht=67,
    ),
    "BN": dict(
        vin=10, vout=11, win=12, wout=13, tproc_vol=14, tproc_wgt=15,
        fte=30, fte_opm=31, eff_wgt=32, eff_vol=33, eff_wgt_opm=34, eff_vol_opm=35,
        bl=47, bl24=48,
        cot_total=70, cot_ontime=71, cot1am_total=73, cot1am_ontime=74,
        arr24_total=76, arr24_ontime=77,
        shc=79, lhc=80, sht=81, lht=82,
    ),
    "SH": dict(
        vin=16, vout=17, win=18, wout=19, tproc_vol=20, tproc_wgt=21,
        fte=36, fte_opm=37, eff_wgt=38, eff_vol=39, eff_wgt_opm=40, eff_vol_opm=41,
        bl=50, bl24=51,
        cot_total=85, cot_ontime=86, cot1am_total=88, cot1am_ontime=89,
        arr24_total=91, arr24_ontime=92,
        shc=94, lhc=95, sht=96, lht=97,
    ),
}

EMPTY_HUB = (pd.DataFrame(), {})


@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token API Feishu.")
        return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB

    # NOTE: sheet đã dài hơn hẳn do chèn thêm khối Năng suất/FTE + Trung
    # chuyển 24H -> tăng vùng fetch từ AQ85 lên AQ150 để không bị cắt dữ liệu.
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ150?valueRenderOption=FormattedValue"
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
                    return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB
            else:
                st.error(f"Lỗi từ Feishu API: {res.get('msg')}")
                return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB
        except Exception as e:
            st.error(f"Lỗi kết nối: {str(e)}")
            return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB

    if not res_data:
        return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals:
        st.error("File Feishu trống!")
        return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB

    if len(vals) < 98:
        st.error(f"File chỉ có {len(vals)} dòng, cần ít nhất 98 (do sheet đã thêm khối FTE/Trung chuyển 24H).")
        return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB

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

        def extract_hub_data(rows):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}

            def col(row_key):
                return [clean_val(rows[row_key], c) for c in cols_to_scan]

            data["Inbound Vol"]        = col('vin')
            data["Outbound Vol"]       = col('vout')
            data["Inbound Wgt"]        = col('win')
            data["Outbound Wgt"]       = col('wout')
            data["Total Process Vol"]  = col('tproc_vol')
            data["Total Process Wgt"]  = col('tproc_wgt')

            data["Backlog"]            = col('bl')
            data["Backlog 24H"]        = col('bl24')

            data["COT Total"]          = col('cot_total')
            data["COT Ontime"]         = col('cot_ontime')
            data["COT Rate (%)"]       = [
                (o / t * 100) if (t and t > 0) else np.nan
                for t, o in zip(data["COT Total"], data["COT Ontime"])
            ]
            data["COT 1AM Total"]      = col('cot1am_total')
            data["COT 1AM Ontime"]     = col('cot1am_ontime')
            data["COT 1AM Rate (%)"]   = [
                (o / t * 100) if (t and t > 0) else np.nan
                for t, o in zip(data["COT 1AM Total"], data["COT 1AM Ontime"])
            ]

            # ── MỚI: Trung chuyển kịp thời trước 24:00 ──
            data["Arr24 Total"]        = col('arr24_total')
            data["Arr24 Ontime"]       = col('arr24_ontime')
            data["Arr24 Rate (%)"]     = [
                (o / t * 100) if (t and t > 0) else np.nan
                for t, o in zip(data["Arr24 Total"], data["Arr24 Ontime"])
            ]

            data["Shuttle Chuyến"]     = col('shc')
            data["Linehaul Chuyến"]    = col('lhc')
            data["Shuttle Late"]       = col('sht')
            data["Linehaul Late"]      = col('lht')
            data["LH Rate (%)"]        = [
                (c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan
                for c, t in zip(data["Linehaul Chuyến"], data["Linehaul Late"])
            ]
            data["SH Rate (%)"]        = [
                (c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan
                for c, t in zip(data["Shuttle Chuyến"], data["Shuttle Late"])
            ]

            # ── MỚI: Năng suất lao động / FTE ──
            data["FTE"]                          = col('fte')
            data["FTE (O+P+M)"]                  = col('fte_opm')
            data["Hiệu suất KG/Người"]           = col('eff_wgt')
            data["Hiệu suất Kiện/Người"]         = col('eff_vol')
            data["Hiệu suất KG/Người (OPM)"]     = col('eff_wgt_opm')
            data["Hiệu suất Kiện/Người (OPM)"]   = col('eff_vol_opm')

            valid_weeks = [
                idx for idx in weekly_col_idxs
                if pd.notna(clean_val(rows['vin'], idx)) and clean_val(rows['vin'], idx) > 0
            ]
            cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
            pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

            def v(row_key, cidx):
                return clean_val(rows[row_key], cidx) if cidx != -1 else 0

            def rate_pair(num_key, den_key, cidx):
                if cidx == -1:
                    return 0
                n = clean_val(rows[num_key], cidx)
                d = clean_val(rows[den_key], cidx)
                return (n / d * 100) if (d and d > 0) else 0

            def lhot(cidx):
                if cidx == -1:
                    return 0
                lhc = clean_val(rows['lhc'], cidx)
                lht = clean_val(rows['lht'], cidx)
                return (lhc - lht) / lhc * 100 if lhc and lhc > 0 else 0

            def shot(cidx):
                if cidx == -1:
                    return 0
                shc = clean_val(rows['shc'], cidx)
                sht = clean_val(rows['sht'], cidx)
                return (shc - sht) / shc * 100 if shc and shc > 0 else 0

            weekly_summary = {
                "cw_vin":       v('vin', cw_idx),       "pw_vin":       v('vin', pw_idx),
                "cw_vout":      v('vout', cw_idx),      "pw_vout":      v('vout', pw_idx),
                "cw_win":       v('win', cw_idx),       "pw_win":       v('win', pw_idx),
                "cw_wout":      v('wout', cw_idx),      "pw_wout":      v('wout', pw_idx),
                "cw_tproc_wgt": v('tproc_wgt', cw_idx), "pw_tproc_wgt": v('tproc_wgt', pw_idx),

                "cw_bl":        v('bl', cw_idx),        "pw_bl":        v('bl', pw_idx),
                "cw_bl_24h":    v('bl24', cw_idx),      "pw_bl_24h":    v('bl24', pw_idx),

                "cw_cot_ontime": v('cot_ontime', cw_idx), "pw_cot_ontime": v('cot_ontime', pw_idx),
                "cw_cot_1am_ontime": v('cot1am_ontime', cw_idx), "pw_cot_1am_ontime": v('cot1am_ontime', pw_idx),
                "cw_cot": rate_pair('cot_ontime', 'cot_total', cw_idx),
                "pw_cot": rate_pair('cot_ontime', 'cot_total', pw_idx),
                "cw_cot_1am": rate_pair('cot1am_ontime', 'cot1am_total', cw_idx),
                "pw_cot_1am": rate_pair('cot1am_ontime', 'cot1am_total', pw_idx),

                # ── MỚI: Trung chuyển 24H ──
                "cw_arr24_total":  v('arr24_total', cw_idx),  "pw_arr24_total":  v('arr24_total', pw_idx),
                "cw_arr24_ontime": v('arr24_ontime', cw_idx), "pw_arr24_ontime": v('arr24_ontime', pw_idx),
                "cw_arr24": rate_pair('arr24_ontime', 'arr24_total', cw_idx),
                "pw_arr24": rate_pair('arr24_ontime', 'arr24_total', pw_idx),

                "cw_lhot": lhot(cw_idx), "pw_lhot": lhot(pw_idx),
                "cw_shot": shot(cw_idx), "pw_shot": shot(pw_idx),

                # ── MỚI: FTE / Năng suất ──
                "cw_fte":     v('fte', cw_idx),     "pw_fte":     v('fte', pw_idx),
                "cw_fte_opm": v('fte_opm', cw_idx), "pw_fte_opm": v('fte_opm', pw_idx),
                "cw_eff_wgt": v('eff_wgt', cw_idx), "pw_eff_wgt": v('eff_wgt', pw_idx),
                "cw_eff_vol": v('eff_vol', cw_idx), "pw_eff_vol": v('eff_vol', pw_idx),
                "cw_eff_wgt_opm": v('eff_wgt_opm', cw_idx), "pw_eff_wgt_opm": v('eff_wgt_opm', pw_idx),
                "cw_eff_vol_opm": v('eff_vol_opm', cw_idx), "pw_eff_vol_opm": v('eff_vol_opm', pw_idx),
            }
            return pd.DataFrame(data), weekly_summary

        data_hcm = extract_hub_data(HUB_ROWS["HCM"])
        data_bn  = extract_hub_data(HUB_ROWS["BN"])
        data_sh  = extract_hub_data(HUB_ROWS["SH"])
        return data_hcm, data_bn, data_sh

    except Exception as e:
        st.error(f"Lỗi xử lý dữ liệu: {str(e)}")
        return EMPTY_HUB, EMPTY_HUB, EMPTY_HUB

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
    sh_mtd         = (df['Shuttle Chuyến'].sum() - df['Shuttle Late'].sum()) / df['Shuttle Chuyến'].sum() * 100 if df['Shuttle Chuyến'].sum() > 0 else 0

    # ── MỚI: Trung chuyển 24H ──
    arr24_total_mtd  = df['Arr24 Total'].sum(skipna=True)
    arr24_ontime_mtd = df['Arr24 Ontime'].sum(skipna=True)
    arr24_mtd        = (arr24_ontime_mtd / arr24_total_mtd * 100) if arr24_total_mtd > 0 else 0

    # ── MỚI: FTE / Năng suất (dùng trung bình vì đây là chỉ số snapshot, không phải lũy kế) ──
    fte_mtd         = df['FTE'].mean(skipna=True)
    fte_opm_mtd     = df['FTE (O+P+M)'].mean(skipna=True)
    eff_wgt_mtd     = df['Hiệu suất KG/Người'].mean(skipna=True)
    eff_vol_mtd     = df['Hiệu suất Kiện/Người'].mean(skipna=True)
    eff_wgt_opm_mtd = df['Hiệu suất KG/Người (OPM)'].mean(skipna=True)
    eff_vol_opm_mtd = df['Hiệu suất Kiện/Người (OPM)'].mean(skipna=True)

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

        # ── MỚI: Trung chuyển 24H ──
        build_row("Trung chuyển 24H", 3, "Đơn đến trước 24:00", summary['cw_arr24_total'], summary['pw_arr24_total'], arr24_total_mtd, 'Arr24 Total', is_first=True),
        build_row("", 0, "Đơn đúng giờ <24:00", summary['cw_arr24_ontime'], summary['pw_arr24_ontime'], arr24_ontime_mtd, 'Arr24 Ontime'),
        build_row("", 0, "Tỷ lệ kịp thời (%)", summary['cw_arr24'], summary['pw_arr24'], arr24_mtd, 'Arr24 Rate (%)', is_pct=True),

        build_row("Vận tải", 2, "Linehaul Ontime (%)", summary['cw_lhot'], summary['pw_lhot'], lhot_mtd, 'LH Rate (%)', is_pct=True, is_first=True),
        build_row("", 0, "Shuttle Ontime (%)", summary['cw_shot'], summary['pw_shot'], sh_mtd, 'SH Rate (%)', is_pct=True),

        # ── MỚI: Năng suất lao động / FTE ──
        build_row("Năng suất", 6, "FTE", summary['cw_fte'], summary['pw_fte'], fte_mtd, 'FTE', is_first=True),
        build_row("", 0, "FTE (O+P+M)", summary['cw_fte_opm'], summary['pw_fte_opm'], fte_opm_mtd, 'FTE (O+P+M)'),
        build_row("", 0, "Hiệu suất KG/Người", summary['cw_eff_wgt'], summary['pw_eff_wgt'], eff_wgt_mtd, 'Hiệu suất KG/Người'),
        build_row("", 0, "Hiệu suất Kiện/Người", summary['cw_eff_vol'], summary['pw_eff_vol'], eff_vol_mtd, 'Hiệu suất Kiện/Người'),
        build_row("", 0, "Hiệu suất KG/Người (OPM)", summary['cw_eff_wgt_opm'], summary['pw_eff_wgt_opm'], eff_wgt_opm_mtd, 'Hiệu suất KG/Người (OPM)'),
        build_row("", 0, "Hiệu suất Kiện/Người (OPM)", summary['cw_eff_vol_opm'], summary['pw_eff_vol_opm'], eff_vol_opm_mtd, 'Hiệu suất Kiện/Người (OPM)'),
    ]

    _thead = (
        f'<th style="width:80px">Nhóm</th>'
        f'<th style="text-align:left">Chỉ số</th>'
        f'{header_wow}'
        f'<th style="width:90px">Lũy kế</th>'
        f'{daily_hdrs}'
    )
    _html(f'<div class="kpi-wrap"><table class="kpi-table"><thead><tr>{_thead}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>', height=760 if show_weekly else 700)

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

    # ── MỚI: Năng suất lao động ──
    st.markdown('<div class="section-header"><div class="section-header-text">Năng suất lao động & Trung chuyển 24H</div></div>', unsafe_allow_html=True)
    c7, c8, c9 = st.columns(3)

    with c7:
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=df['Ngày'], y=df['FTE'], name="FTE", mode='lines+markers', line=dict(color='#0078D4', width=2)))
        fig7.add_trace(go.Scatter(x=df['Ngày'], y=df['FTE (O+P+M)'], name="FTE (O+P+M)", mode='lines+markers', line=dict(color='#605E5C', width=2, dash='dot')))
        st.plotly_chart(clean_layout(fig7, "FTE theo ngày"), use_container_width=True, key=f"{hub_name}_{period_label}_7")

    with c8:
        fig8 = go.Figure()
        fig8.add_trace(go.Bar(x=df['Ngày'], y=df['Hiệu suất KG/Người'], name="KG/Người", marker_color='#2899F5'))
        fig8.add_trace(go.Scatter(x=df['Ngày'], y=df['Hiệu suất Kiện/Người'], name="Kiện/Người", yaxis="y2", line=dict(color='#FFB900', width=2), mode='lines+markers'))
        fig8 = clean_layout(fig8, "Hiệu suất bình quân đầu người")
        fig8.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False))
        st.plotly_chart(fig8, use_container_width=True, key=f"{hub_name}_{period_label}_8")

    with c9:
        fig10 = go.Figure()
        fig10.add_trace(go.Bar(x=df['Ngày'], y=df['Arr24 Total'], name="Tổng đơn", marker_color='#E1DFDD'))
        fig10.add_trace(go.Scatter(x=df['Ngày'], y=df['Arr24 Rate (%)'], name="Tỷ lệ (%)", yaxis="y2", line=dict(color='#107C10', width=2), mode='lines+markers'))
        fig10 = clean_layout(fig10, "Tỷ lệ trung chuyển kịp 24:00")
        fig10.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False))
        st.plotly_chart(fig10, use_container_width=True, key=f"{hub_name}_{period_label}_10")

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

# ── Load data (chỉ gọi get_data() 1 LẦN — tránh gọi 3 lần lãng phí request) ──
(df_hcm, sum_hcm), (df_bn, sum_bn), (df_sh, sum_sh) = get_data()

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
