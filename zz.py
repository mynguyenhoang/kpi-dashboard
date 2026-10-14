import os
import streamlit.components.v1 as components
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }
:root {
    --bg-main:    #F3F2F1;
    --surface:    #FFFFFF;
    --border:     #E1DFDD;
    --text-main:  #323130;
    --text-muted: #605E5C;
    --primary:    #0078D4;
    --green:      #107C10;
    --red:        #D13438;
    --shadow-sm:  0 1.6px 3.6px 0 rgba(0,0,0,0.132), 0 0.3px 0.9px 0 rgba(0,0,0,0.108);
    --radius:     4px;
    --font:       'Inter', 'Segoe UI', sans-serif;
    --font-mono:  'JetBrains Mono', monospace;
}

.stApp, [data-testid="stAppViewContainer"] {
    background: var(--bg-main) !important;
    font-family: var(--font) !important;
}
body, p, div, span, td, th, label, input, button {
    font-family: var(--font) !important;
    color: var(--text-main);
}

#MainMenu, header, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stHeader"] {
    visibility: hidden !important;
    height: 0 !important;
}

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
def _secret(key):
    """Đọc key từ .streamlit/secrets.toml hoặc biến môi trường."""
    try:
        val = st.secrets[key]
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key)


def get_tenant_access_token():
    app_id = _secret("FEISHU_APP_ID")
    app_secret = _secret("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        st.error("Thiếu FEISHU_APP_ID / FEISHU_APP_SECRET (đặt trong .streamlit/secrets.toml hoặc biến môi trường).")
        return None
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except Exception as e:
        st.error(f"Lỗi lấy Token Feishu: {str(e)}")
        return None


# ─────────────────────────────────────────────────────────────
# MAP INDEX HÀNG (0-based, khớp "Index N" của công cụ dò)
#
#   Sản lượng   : 6 dòng/hub  → HCM 4 | BN 10 | SH 16 | CTO 22
#   Năng suất   : 6 dòng/hub  → HCM 30 | BN 36 | SH 42 | CTO 48
#   Tồn ứ       : 3 dòng/hub  → HCM 56 | BN 59 | SH 62 | CTO 65
#   Linehaul/COT: 24 dòng/hub → HCM 70 | BN 94 | SH 118 | CTO 142
#
#   Offset trong khối Linehaul/COT (base = lh):
#     +0 COT total      +1 COT ontime      +2 (%)
#     +3 1AM total      +4 1AM ontime      +5 (%)
#     +6 Arr24 total    +7 Arr24 ontime    +8 (%)
#     +9  Chuyến tuyến chính đến đúng hạn
#     +10 Chuyến tuyến chính dỡ hàng đúng hạn   +11 Tỷ lệ dỡ hàng (%)
#     +12 Đơn tuyến chính đến đúng hạn
#     +13 Đơn tuyến chính gửi đúng hạn          +14 Tỷ lệ gửi tuyến chính (%)
#     +15 Đơn tuyến nhánh đến đúng hạn
#     +16 Đơn tuyến nhánh gửi đúng hạn          +17 Tỷ lệ gửi tuyến nhánh (%)
#     +18 Shuttle chuyến  +19 Linehaul chuyến
#     +20 Shuttle trễ     +21 Linehaul trễ
#     +22 % Shuttle ontime  +23 % LH ontime
# ─────────────────────────────────────────────────────────────
def make_rows(prod, eff, bl, lh):
    return dict(
        vin=prod, vout=prod + 1, win=prod + 2, wout=prod + 3,
        tproc_vol=prod + 4, tproc_wgt=prod + 5,
        fte=eff, fte_opm=eff + 1, eff_wgt=eff + 2, eff_vol=eff + 3,
        eff_wgt_opm=eff + 4, eff_vol_opm=eff + 5,
        bl=bl, bl24=bl + 1, bl24_rate=bl + 2,
        cot_total=lh, cot_ontime=lh + 1,
        cot1am_total=lh + 3, cot1am_ontime=lh + 4,
        arr24_total=lh + 6, arr24_ontime=lh + 7,
        lh_arr_trip=lh + 9, lh_unl_trip=lh + 10, lh_unl_rate=lh + 11,
        lh_arr_tix=lh + 12, lh_dep_tix=lh + 13, lh_dep_rate=lh + 14,
        br_arr_tix=lh + 15, br_dep_tix=lh + 16, br_dep_rate=lh + 17,
        shc=lh + 18, lhc=lh + 19, sht=lh + 20, lht=lh + 21,
    )


HUB_ROWS = {
    "HCM": make_rows(4, 30, 56, 70),
    "BN":  make_rows(10, 36, 59, 94),
    "SH":  make_rows(16, 42, 62, 118),
    "CTO": make_rows(22, 48, 65, 142),
}

MAX_ROW_INDEX = max(max(r.values()) for r in HUB_ROWS.values())  # = 165
EMPTY_HUB = (pd.DataFrame(), {})
EMPTY_ALL = (EMPTY_HUB, EMPTY_HUB, EMPTY_HUB, EMPTY_HUB)


@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token API Feishu.")
        return EMPTY_ALL

    fetch_rows = MAX_ROW_INDEX + 10  # dư vài dòng cho an toàn
    url = (
        "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/"
        f"NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ{fetch_rows}"
        "?valueRenderOption=FormattedValue"
    )
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
                    return EMPTY_ALL
            else:
                st.error(f"Lỗi từ Feishu API: {res.get('msg')}")
                return EMPTY_ALL
        except Exception as e:
            st.error(f"Lỗi kết nối: {str(e)}")
            return EMPTY_ALL

    if not res_data:
        return EMPTY_ALL

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals:
        st.error("File Feishu trống!")
        return EMPTY_ALL

    if len(vals) <= MAX_ROW_INDEX:
        st.error(f"File chỉ có {len(vals)} dòng, cần ít nhất {MAX_ROW_INDEX + 1} (đến Index {MAX_ROW_INDEX}).")
        return EMPTY_ALL

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
        except Exception:
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

        def safe_rate(ontime, total):
            return [
                (o / t * 100) if (pd.notna(t) and t > 0 and pd.notna(o)) else np.nan
                for t, o in zip(total, ontime)
            ]

        def late_rate(trips, late):
            return [
                (c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan
                for c, t in zip(trips, late)
            ]

        def extract_hub_data(rows):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}

            def col(row_key):
                return [clean_val(rows[row_key], c) for c in cols_to_scan]

            # ── Sản lượng ──
            data["Inbound Vol"]        = col('vin')
            data["Outbound Vol"]       = col('vout')
            data["Inbound Wgt"]        = col('win')
            data["Outbound Wgt"]       = col('wout')
            data["Total Process Vol"]  = col('tproc_vol')
            data["Total Process Wgt"]  = col('tproc_wgt')

            # ── Tồn ứ ──
            data["Backlog"]            = col('bl')
            data["Backlog 24H"]        = col('bl24')
            data["Backlog 24H Rate (%)"] = col('bl24_rate')

            # ── COT / 1AM ──
            data["COT Total"]          = col('cot_total')
            data["COT Ontime"]         = col('cot_ontime')
            data["COT Rate (%)"]       = safe_rate(data["COT Ontime"], data["COT Total"])
            data["COT 1AM Total"]      = col('cot1am_total')
            data["COT 1AM Ontime"]     = col('cot1am_ontime')
            data["COT 1AM Rate (%)"]   = safe_rate(data["COT 1AM Ontime"], data["COT 1AM Total"])

            # ── Trung chuyển kịp thời trước 24:00 ──
            data["Arr24 Total"]        = col('arr24_total')
            data["Arr24 Ontime"]       = col('arr24_ontime')
            data["Arr24 Rate (%)"]     = safe_rate(data["Arr24 Ontime"], data["Arr24 Total"])

            # ── Tuyến chính / tuyến nhánh (MỚI) ──
            data["LH Arr Trips Ontime"]    = col('lh_arr_trip')
            data["LH Unload Trips Ontime"] = col('lh_unl_trip')
            data["LH Unload Rate (%)"]     = col('lh_unl_rate')
            data["LH Arr Tickets Ontime"]  = col('lh_arr_tix')
            data["LH Dep Tickets Ontime"]  = col('lh_dep_tix')
            data["LH Dep Rate (%)"]        = col('lh_dep_rate')
            data["BR Arr Tickets Ontime"]  = col('br_arr_tix')
            data["BR Dep Tickets Ontime"]  = col('br_dep_tix')
            data["BR Dep Rate (%)"]        = col('br_dep_rate')

            # ── Vận tải ──
            data["Shuttle Chuyến"]     = col('shc')
            data["Linehaul Chuyến"]    = col('lhc')
            data["Shuttle Late"]       = col('sht')
            data["Linehaul Late"]      = col('lht')
            data["LH Rate (%)"]        = late_rate(data["Linehaul Chuyến"], data["Linehaul Late"])
            data["SH Rate (%)"]        = late_rate(data["Shuttle Chuyến"], data["Shuttle Late"])

            # ── Năng suất lao động / FTE ──
            data["FTE"]                        = col('fte')
            data["FTE (O+P+M)"]                = col('fte_opm')
            data["Hiệu suất KG/Người"]         = col('eff_wgt')
            data["Hiệu suất Kiện/Người"]       = col('eff_vol')
            data["Hiệu suất KG/Người (OPM)"]   = col('eff_wgt_opm')
            data["Hiệu suất Kiện/Người (OPM)"] = col('eff_vol_opm')

            # ── Tuần này / tuần trước ──
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

            def late_pct(trip_key, late_key, cidx):
                if cidx == -1:
                    return 0
                c = clean_val(rows[trip_key], cidx)
                t = clean_val(rows[late_key], cidx)
                if not (pd.notna(c) and c > 0):
                    return 0
                return (c - (t if pd.notna(t) else 0)) / c * 100

            # Mọi dòng trong HUB_ROWS đều có cw_<key> / pw_<key>
            weekly_summary = {}
            for k in rows:
                weekly_summary[f"cw_{k}"] = v(k, cw_idx)
                weekly_summary[f"pw_{k}"] = v(k, pw_idx)

            # Các tỷ lệ tính từ tử/mẫu
            weekly_summary.update({
                "cw_cot":     rate_pair('cot_ontime', 'cot_total', cw_idx),
                "pw_cot":     rate_pair('cot_ontime', 'cot_total', pw_idx),
                "cw_cot_1am": rate_pair('cot1am_ontime', 'cot1am_total', cw_idx),
                "pw_cot_1am": rate_pair('cot1am_ontime', 'cot1am_total', pw_idx),
                "cw_arr24":   rate_pair('arr24_ontime', 'arr24_total', cw_idx),
                "pw_arr24":   rate_pair('arr24_ontime', 'arr24_total', pw_idx),
                "cw_lhot":    late_pct('lhc', 'lht', cw_idx),
                "pw_lhot":    late_pct('lhc', 'lht', pw_idx),
                "cw_shot":    late_pct('shc', 'sht', cw_idx),
                "pw_shot":    late_pct('shc', 'sht', pw_idx),
            })
            return pd.DataFrame(data), weekly_summary

        return (
            extract_hub_data(HUB_ROWS["HCM"]),
            extract_hub_data(HUB_ROWS["BN"]),
            extract_hub_data(HUB_ROWS["SH"]),
            extract_hub_data(HUB_ROWS["CTO"]),
        )

    except Exception as e:
        st.error(f"Lỗi xử lý dữ liệu: {str(e)}")
        return EMPTY_ALL

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
    if pd.isna(number) or number == "":
        return ""
    return f"{number:,.0f}".replace(",", ".")


def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) and pd.isna(prev):
        return "<td class='col-num status-neutral'>—</td><td class='col-num'></td><td class='col-num'></td>"
    if pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct and pd.notna(cur) else fmt_vn(cur)
        if pd.isna(cur):
            cur_str = "—"
        return f"<td class='col-num status-neutral'>—</td><td class='col-num'>{cur_str}</td><td class='col-num'>—</td>"
    if pd.isna(cur):
        prev_str = f"{prev:.2f}%" if is_pct else fmt_vn(prev)
        return f"<td class='col-num status-neutral'>—</td><td class='col-num'>—</td><td class='col-num'>{prev_str}</td>"

    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    is_positive = diff > 0
    good = (is_positive and not inverse) or (not is_positive and inverse)

    status_class = "status-good" if good else "status-bad" if diff != 0 else "status-neutral"
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "-"

    wow_str = f"{arrow} {abs(pct):.1f}%" if diff != 0 else "-"
    cur_str = fmt_vn(cur) if not is_pct else f"{cur:.1f}%"
    prev_str = fmt_vn(prev) if not is_pct else f"{prev:.1f}%"

    return (
        f"<td class='col-num {status_class}'>{wow_str}</td>"
        f"<td class='col-num'>{cur_str}</td>"
        f"<td class='col-num' style='color:#605E5C'>{prev_str}</td>"
    )

# ════════════════════════════════════════════════════════════
# 4. CHART THEME
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
    if df.empty:
        return df
    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    if valid_df.empty:
        return df.tail(7).reset_index(drop=True)
    last_idx = valid_df.index[-1]
    start_idx = max(0, last_idx - 6)
    return df.iloc[start_idx:last_idx + 1].reset_index(drop=True)


def render_dashboard(df, summary, hub_name, period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=False):
    if df.empty:
        st.info(f"Chưa có dữ liệu cho {hub_name}.")
        return

    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    if valid_df.empty:
        st.info(f"{hub_name}: chưa có ngày nào có dữ liệu Inbound.")
        return

    actual_cols = min(len(valid_df), num_daily_cols)
    data_slice = valid_df.tail(actual_cols + 1).reset_index(drop=True)

    if len(data_slice) > actual_cols:
        d_names = data_slice['Ngày'].tolist()[1:]
    else:
        d_names = data_slice['Ngày'].tolist()

    pad_len = num_daily_cols - len(d_names)
    d_display = ["-"] * pad_len + d_names

    # ── Hàm vẽ cell ngày ──
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
                cells.append("<td class='col-num' style='color:#C8C6C4'>—</td>")
                continue

            cur_str = f"{cur:.1f}%" if is_pct else fmt_vn(cur)

            if pd.notna(prev) and prev != cur:
                diff = cur - prev
                going_up = diff > 0
                good = (going_up and not inverse) or (not going_up and inverse)
                arrow = "▲" if going_up else "▼"
                status_color = "#107C10" if good else "#D13438"
                indicator = f"<span style='color:{status_color}; font-size:11px; margin-left:4px;'>{arrow}</span>"
                cells.append(f"<td class='col-num'>{cur_str}{indicator}</td>")
            else:
                cells.append(f"<td class='col-num'>{cur_str}</td>")
        return "".join(cells)

    # ── Tổng hợp MTD ──
    def ssum(c):
        return df[c].sum(skipna=True)

    def smean(c):
        return df[c].mean(skipna=True)

    def ratio(num_col, den_col):
        d = ssum(den_col)
        return ssum(num_col) / d * 100 if d > 0 else np.nan

    t_vin = ssum('Inbound Vol')
    t_vout = ssum('Outbound Vol')
    t_tproc_vol = ssum('Total Process Vol')
    t_tproc_wgt = ssum('Total Process Wgt')
    t_bl = ssum('Backlog')
    t_bl24 = ssum('Backlog 24H')
    bl24_rate_mtd = (t_bl24 / t_bl * 100) if t_bl > 0 else np.nan

    cot_mtd = ratio('COT Ontime', 'COT Total')
    cot_1am_mtd = ratio('COT 1AM Ontime', 'COT 1AM Total')
    arr24_mtd = ratio('Arr24 Ontime', 'Arr24 Total')

    lh_total = ssum('Linehaul Chuyến')
    sh_total = ssum('Shuttle Chuyến')
    lhot_mtd = (lh_total - ssum('Linehaul Late')) / lh_total * 100 if lh_total > 0 else np.nan
    sh_mtd = (sh_total - ssum('Shuttle Late')) / sh_total * 100 if sh_total > 0 else np.nan

    # ── KPI Cards ──
    CARDS = [
        ("Inbound", t_vin),
        ("Outbound", t_vout),
        ("Sản lượng xử lý", t_tproc_vol),
        ("Trọng lượng (kg)", t_tproc_wgt),
        ("Tồn kho (Backlog)", t_bl),
    ]
    cols = st.columns(5)
    for col_obj, (title, val) in zip(cols, CARDS):
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

    def build_row(kpi_title, rowspan, metric_name, wow_cur, wow_prev, mtd_val, col_name,
                  is_pct=False, inverse=False, is_first=False):
        kpi_td = f'<td rowspan="{rowspan}" class="col-pillar">{kpi_title}</td>' if is_first else ''
        wow_td = get_wow_cell(wow_cur, wow_prev, is_pct, inverse) if show_weekly else ''
        if is_pct:
            mtd_str = "—" if pd.isna(mtd_val) else f"{mtd_val:.1f}%"
        else:
            mtd_str = fmt_vn(mtd_val)
        d_tds = get_d(col_name, is_pct, inverse)
        return (
            f"<tr>{kpi_td}"
            f"<td class='col-metric'>{metric_name}</td>"
            f"{wow_td}"
            f"<td class='col-mtd'>{mtd_str}</td>"
            f"{d_tds}</tr>"
        )

    S = summary

    def w(key):
        """Trả về (tuần này, tuần trước) cho 1 key."""
        return S.get(f"cw_{key}", np.nan), S.get(f"pw_{key}", np.nan)

    rows = [
        # ── Sản lượng (4) ──
        build_row("Sản lượng", 4, "Inbound", *w('vin'), t_vin, 'Inbound Vol', is_first=True),
        build_row("", 0, "Outbound", *w('vout'), t_vout, 'Outbound Vol'),
        build_row("", 0, "Trọng lượng Inbound", *w('win'), ssum('Inbound Wgt'), 'Inbound Wgt'),
        build_row("", 0, "Trọng lượng Outbound", *w('wout'), ssum('Outbound Wgt'), 'Outbound Wgt'),

        # ── Chất lượng (7) ──
        build_row("Chất lượng", 7, "Backlog", *w('bl'), t_bl, 'Backlog', inverse=True, is_first=True),
        build_row("", 0, "Backlog >24H", *w('bl24'), t_bl24, 'Backlog 24H', inverse=True),
        build_row("", 0, "Tỷ lệ Backlog >24H (%)", *w('bl24_rate'), bl24_rate_mtd, 'Backlog 24H Rate (%)', is_pct=True, inverse=True),
        build_row("", 0, "Đơn đúng COT", *w('cot_ontime'), ssum('COT Ontime'), 'COT Ontime'),
        build_row("", 0, "Tỷ lệ Ontime (%)", *w('cot'), cot_mtd, 'COT Rate (%)', is_pct=True),
        build_row("", 0, "Đơn đúng 1AM", *w('cot1am_ontime'), ssum('COT 1AM Ontime'), 'COT 1AM Ontime'),
        build_row("", 0, "Tỷ lệ 1AM (%)", *w('cot_1am'), cot_1am_mtd, 'COT 1AM Rate (%)', is_pct=True),

        # ── Trung chuyển 24H (3) ──
        build_row("Trung chuyển 24H", 3, "Đơn đến trước 24:00", *w('arr24_total'), ssum('Arr24 Total'), 'Arr24 Total', is_first=True),
        build_row("", 0, "Đơn đúng giờ <24:00", *w('arr24_ontime'), ssum('Arr24 Ontime'), 'Arr24 Ontime'),
        build_row("", 0, "Tỷ lệ kịp thời (%)", *w('arr24'), arr24_mtd, 'Arr24 Rate (%)', is_pct=True),

        # ── Tuyến chính / nhánh (9) — MỚI ──
        build_row("Tuyến chính / nhánh", 9, "Chuyến tuyến chính đến đúng hạn", *w('lh_arr_trip'), ssum('LH Arr Trips Ontime'), 'LH Arr Trips Ontime', is_first=True),
        build_row("", 0, "Chuyến tuyến chính dỡ hàng đúng hạn", *w('lh_unl_trip'), ssum('LH Unload Trips Ontime'), 'LH Unload Trips Ontime'),
        build_row("", 0, "Tỷ lệ dỡ hàng tuyến chính (%)", *w('lh_unl_rate'), smean('LH Unload Rate (%)'), 'LH Unload Rate (%)', is_pct=True),
        build_row("", 0, "Đơn tuyến chính đến đúng hạn", *w('lh_arr_tix'), ssum('LH Arr Tickets Ontime'), 'LH Arr Tickets Ontime'),
        build_row("", 0, "Đơn tuyến chính gửi đúng hạn", *w('lh_dep_tix'), ssum('LH Dep Tickets Ontime'), 'LH Dep Tickets Ontime'),
        build_row("", 0, "Tỷ lệ gửi tuyến chính (%)", *w('lh_dep_rate'), smean('LH Dep Rate (%)'), 'LH Dep Rate (%)', is_pct=True),
        build_row("", 0, "Đơn tuyến nhánh đến đúng hạn", *w('br_arr_tix'), ssum('BR Arr Tickets Ontime'), 'BR Arr Tickets Ontime'),
        build_row("", 0, "Đơn tuyến nhánh gửi đúng hạn", *w('br_dep_tix'), ssum('BR Dep Tickets Ontime'), 'BR Dep Tickets Ontime'),
        build_row("", 0, "Tỷ lệ gửi tuyến nhánh (%)", *w('br_dep_rate'), smean('BR Dep Rate (%)'), 'BR Dep Rate (%)', is_pct=True),

        # ── Vận tải (2) ──
        build_row("Vận tải", 2, "Linehaul Ontime (%)", *w('lhot'), lhot_mtd, 'LH Rate (%)', is_pct=True, is_first=True),
        build_row("", 0, "Shuttle Ontime (%)", *w('shot'), sh_mtd, 'SH Rate (%)', is_pct=True),

        # ── Năng suất (6) — chỉ số snapshot nên MTD dùng trung bình ──
        build_row("Năng suất", 6, "FTE", *w('fte'), smean('FTE'), 'FTE', is_first=True),
        build_row("", 0, "FTE (O+P+M)", *w('fte_opm'), smean('FTE (O+P+M)'), 'FTE (O+P+M)'),
        build_row("", 0, "Hiệu suất KG/Người", *w('eff_wgt'), smean('Hiệu suất KG/Người'), 'Hiệu suất KG/Người'),
        build_row("", 0, "Hiệu suất Kiện/Người", *w('eff_vol'), smean('Hiệu suất Kiện/Người'), 'Hiệu suất Kiện/Người'),
        build_row("", 0, "Hiệu suất KG/Người (OPM)", *w('eff_wgt_opm'), smean('Hiệu suất KG/Người (OPM)'), 'Hiệu suất KG/Người (OPM)'),
        build_row("", 0, "Hiệu suất Kiện/Người (OPM)", *w('eff_vol_opm'), smean('Hiệu suất Kiện/Người (OPM)'), 'Hiệu suất Kiện/Người (OPM)'),
    ]

    _thead = (
        '<th style="width:80px">Nhóm</th>'
        '<th style="text-align:left">Chỉ số</th>'
        f'{header_wow}'
        '<th style="width:90px">Lũy kế</th>'
        f'{daily_hdrs}'
    )
    _html(
        f'<div class="kpi-wrap"><table class="kpi-table"><thead><tr>{_thead}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        height=1250
    )

    # ══════════════════════════
    # BIỂU ĐỒ
    # ══════════════════════════
    key_base = f"{hub_name}_{period_label}"

    st.markdown('<div class="section-header"><div class="section-header-text">Sản lượng & Năng suất</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", mode='lines+markers', line=dict(color='#0078D4', width=2), marker=dict(size=5)))
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", mode='lines+markers', line=dict(color='#605E5C', width=2, dash='dot'), marker=dict(size=5)))
        st.plotly_chart(clean_layout(fig1, "Inbound vs Outbound"), use_container_width=True, key=f"{key_base}_1")

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#0078D4'))
        st.plotly_chart(clean_layout(fig2, "Tổng đơn xử lý"), use_container_width=True, key=f"{key_base}_2")

    with c3:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#2899F5'))
        st.plotly_chart(clean_layout(fig3, "Tổng trọng lượng (kg)"), use_container_width=True, key=f"{key_base}_3")

    st.markdown('<div class="section-header"><div class="section-header-text">Vận tải & Tỷ lệ hoàn thành (COT)</div></div>', unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)

    with c4:
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Chuyến'], name="Shuttle", marker_color='#A6A6A6'))
        fig4.add_trace(go.Bar(x=df['Ngày'], y=df['Linehaul Chuyến'], name="Linehaul", marker_color='#0078D4'))
        fig4.update_layout(barmode='stack')
        st.plotly_chart(clean_layout(fig4, "Số chuyến xe"), use_container_width=True, key=f"{key_base}_4")

    with c5:
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(x=df['Ngày'], y=df['COT Total'], name="Tổng đơn", marker_color='#E1DFDD'))
        fig5.add_trace(go.Scatter(x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ (%)", yaxis="y2", line=dict(color='#107C10', width=2), mode='lines+markers'))
        fig5 = clean_layout(fig5, "Tỷ lệ Ontime COT")
        fig5.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False))
        st.plotly_chart(fig5, use_container_width=True, key=f"{key_base}_5")

    with c6:
        fig9 = go.Figure()
        fig9.add_trace(go.Bar(x=df['Ngày'], y=df['Backlog'], name="Total", marker_color='#FFB900'))
        fig9.add_trace(go.Bar(x=df['Ngày'], y=df['Backlog 24H'], name=">24H", marker_color='#D13438'))
        fig9.add_trace(go.Scatter(x=df['Ngày'], y=df['Backlog 24H Rate (%)'], name="% >24H", yaxis="y2", line=dict(color='#605E5C', width=2), mode='lines+markers'))
        fig9 = clean_layout(fig9, "Tồn kho (Backlog)")
        fig9.update_layout(barmode='group', yaxis2=dict(overlaying='y', side='right', showgrid=False))
        st.plotly_chart(fig9, use_container_width=True, key=f"{key_base}_9")

    st.markdown('<div class="section-header"><div class="section-header-text">Năng suất lao động & Trung chuyển 24H</div></div>', unsafe_allow_html=True)
    c7, c8, c9 = st.columns(3)

    with c7:
        fig7 = go.Figure()
        fig7.add_trace(go.Scatter(x=df['Ngày'], y=df['FTE'], name="FTE", mode='lines+markers', line=dict(color='#0078D4', width=2)))
        fig7.add_trace(go.Scatter(x=df['Ngày'], y=df['FTE (O+P+M)'], name="FTE (O+P+M)", mode='lines+markers', line=dict(color='#605E5C', width=2, dash='dot')))
        st.plotly_chart(clean_layout(fig7, "FTE theo ngày"), use_container_width=True, key=f"{key_base}_7")

    with c8:
        fig8 = go.Figure()
        fig8.add_trace(go.Bar(x=df['Ngày'], y=df['Hiệu suất KG/Người'], name="KG/Người", marker_color='#2899F5'))
        fig8.add_trace(go.Scatter(x=df['Ngày'], y=df['Hiệu suất Kiện/Người'], name="Kiện/Người", yaxis="y2", line=dict(color='#FFB900', width=2), mode='lines+markers'))
        fig8 = clean_layout(fig8, "Hiệu suất bình quân đầu người")
        fig8.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False))
        st.plotly_chart(fig8, use_container_width=True, key=f"{key_base}_8")

    with c9:
        fig10 = go.Figure()
        fig10.add_trace(go.Bar(x=df['Ngày'], y=df['Arr24 Total'], name="Tổng đơn", marker_color='#E1DFDD'))
        fig10.add_trace(go.Scatter(x=df['Ngày'], y=df['Arr24 Rate (%)'], name="Tỷ lệ (%)", yaxis="y2", line=dict(color='#107C10', width=2), mode='lines+markers'))
        fig10 = clean_layout(fig10, "Tỷ lệ trung chuyển kịp 24:00")
        fig10.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False))
        st.plotly_chart(fig10, use_container_width=True, key=f"{key_base}_10")

    # ── MỚI: Tuyến chính / nhánh ──
    st.markdown('<div class="section-header"><div class="section-header-text">Tuyến chính & Tuyến nhánh</div></div>', unsafe_allow_html=True)
    c10, c11, c12 = st.columns(3)

    with c10:
        fig11 = go.Figure()
        fig11.add_trace(go.Bar(x=df['Ngày'], y=df['LH Arr Trips Ontime'], name="Đến đúng hạn", marker_color='#0078D4'))
        fig11.add_trace(go.Bar(x=df['Ngày'], y=df['LH Unload Trips Ontime'], name="Dỡ hàng đúng hạn", marker_color='#A6A6A6'))
        fig11.add_trace(go.Scatter(x=df['Ngày'], y=df['LH Unload Rate (%)'], name="% dỡ hàng", yaxis="y2", line=dict(color='#107C10', width=2), mode='lines+markers'))
        fig11 = clean_layout(fig11, "Chuyến tuyến chính đúng hạn")
        fig11.update_layout(barmode='group', yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False))
        st.plotly_chart(fig11, use_container_width=True, key=f"{key_base}_11")

    with c11:
        fig12 = go.Figure()
        fig12.add_trace(go.Scatter(x=df['Ngày'], y=df['LH Dep Rate (%)'], name="Tuyến chính", mode='lines+markers', line=dict(color='#0078D4', width=2)))
        fig12.add_trace(go.Scatter(x=df['Ngày'], y=df['BR Dep Rate (%)'], name="Tuyến nhánh", mode='lines+markers', line=dict(color='#FFB900', width=2)))
        fig12 = clean_layout(fig12, "Tỷ lệ gửi hàng đúng hạn")
        fig12.update_layout(yaxis=dict(range=[0, 110], showgrid=True, gridcolor="#F3F2F1"))
        st.plotly_chart(fig12, use_container_width=True, key=f"{key_base}_12")

    with c12:
        fig13 = go.Figure()
        fig13.add_trace(go.Bar(x=df['Ngày'], y=df['LH Arr Tickets Ontime'], name="Chính đến", marker_color='#0078D4'))
        fig13.add_trace(go.Bar(x=df['Ngày'], y=df['LH Dep Tickets Ontime'], name="Chính gửi", marker_color='#2899F5'))
        fig13.add_trace(go.Bar(x=df['Ngày'], y=df['BR Arr Tickets Ontime'], name="Nhánh đến", marker_color='#FFB900'))
        fig13.add_trace(go.Bar(x=df['Ngày'], y=df['BR Dep Tickets Ontime'], name="Nhánh gửi", marker_color='#A6A6A6'))
        fig13 = clean_layout(fig13, "Số đơn đúng hạn (tuyến chính / nhánh)")
        fig13.update_layout(barmode='group')
        st.plotly_chart(fig13, use_container_width=True, key=f"{key_base}_13")

    # ── Raw data toggle ──
    if show_raw_data:
        if st.checkbox("Xem dữ liệu bảng chi tiết", key=f"raw_{key_base}"):
            raw = df.copy()
            for c in raw.columns:
                if c != "Ngày":
                    raw[c] = raw[c].apply(
                        lambda x, c=c: f"{float(x):.1f}%" if "%" in c and pd.notna(x)
                        else (fmt_vn(float(x)) if pd.notna(x) else "")
                    )
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

# Chỉ gọi get_data() 1 lần
(df_hcm, sum_hcm), (df_bn, sum_bn), (df_sh, sum_sh), (df_cto, sum_cto) = get_data()

if df_hcm.empty and df_bn.empty and df_sh.empty and df_cto.empty:
    st.stop()

tabs = st.tabs([
    "Hồ Chí Minh", "Bắc Ninh", "SH DC", "CTO SC",
    "HCM · 7 Ngày", "BN · 7 Ngày", "SH DC · 7 Ngày", "CTO SC · 7 Ngày",
])

with tabs[0]: render_dashboard(df_hcm, sum_hcm, "HCM", "MTD", True, 3, True)
with tabs[1]: render_dashboard(df_bn, sum_bn, "Bắc Ninh", "MTD", True, 3, True)
with tabs[2]: render_dashboard(df_sh, sum_sh, "SH DC", "MTD", True, 3, True)
with tabs[3]: render_dashboard(df_cto, sum_cto, "CTO SC", "MTD", True, 3, True)
with tabs[4]: render_dashboard(get_last_7_days(df_hcm), sum_hcm, "HCM", "7 Ngày", False, 7, False)
with tabs[5]: render_dashboard(get_last_7_days(df_bn), sum_bn, "Bắc Ninh", "7 Ngày", False, 7, False)
with tabs[6]: render_dashboard(get_last_7_days(df_sh), sum_sh, "SH DC", "7 Ngày", False, 7, False)
with tabs[7]: render_dashboard(get_last_7_days(df_cto), sum_cto, "CTO SC", "7 Ngày", False, 7, False)
