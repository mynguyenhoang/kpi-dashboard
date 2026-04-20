import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .kpi-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
        background-color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kpi-table th {
        background-color: #1f2937;
        color: white;
        padding: 10px 12px;
        text-align: center;
        border: 1px solid #d1d5db;
        font-size: 14px;
        font-weight: bold;
    }
    .kpi-table td {
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        font-size: 14px;
        vertical-align: middle;
    }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px 20px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
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

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token Feishu.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        if res.get("code") != 0:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not vals or len(vals) < 50:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if not str_v or "#" in str_v or "=" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else 0.0
            return np.nan
        except:
            return np.nan

    # Xác định số ngày thực tế trong tháng (tránh quét nhầm cột Tổng)
    date_row_idx = 3 
    start_col_idx = 6 # Cột G (Index 6) thường là ngày 1
    num_days = 0
    for c in range(start_col_idx, len(vals[date_row_idx])):
        val = str(vals[date_row_idx][c]).strip()
        if val.isdigit():
            num_days += 1
        else:
            break # Dừng lại khi gặp cột không phải số (ví dụ cột "Total" hoặc "MTD")

    cols_to_scan = [start_col_idx + i for i in range(num_days)]
    weekly_col_idxs = [3, 4, 5, 6] 

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # Logistic
        lh_c = [clean_val(lhc_idx, c) for c in cols_to_scan]
        lh_t = [clean_val(lht_idx, c) for c in cols_to_scan]
        sh_c = [clean_val(shc_idx, c) for c in cols_to_scan]
        sh_t = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        data["LH Đúng Giờ"] = [(c - t) if (pd.notna(c) and c > 0) else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = [t if (pd.notna(t) and t > 0) else (0 if pd.notna(c) else np.nan) for c, t in zip(lh_c, lh_t)]
        data["Shuttle Đúng Giờ"] = [(c - t) if (pd.notna(c) and c > 0) else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = [t if (pd.notna(t) and t > 0) else (0 if pd.notna(c) else np.nan) for c, t in zip(sh_c, sh_t)]

        # Weekly Summary (WOW)
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if not chuyen: return 0
            return ((chuyen - (tre or 0)) / chuyen) * 100

        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), weekly_summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or prev == 0:
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
    
    diff = (cur - prev) if is_pct else (((cur - prev) / prev) * 100)
    if diff > 0.01:
        bg, txt, sign = ("#fee2e2", "#b91c1c", "+") if inverse else ("#dcfce7", "#15803d", "+")
    elif diff < -0.01:
        bg, txt, sign = ("#dcfce7", "#15803d", "") if inverse else ("#fee2e2", "#b91c1c", "")
    else:
        bg, txt, sign = "transparent", "#333", ""
    
    wow_str = f"{sign}{diff:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    
    return f"<td style='background-color: {bg}; color: {txt}; font-weight: bold; text-align: center;'>{wow_str}</td><td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # FIX: Tính MTD bằng cách lọc bỏ các dòng rỗng (chưa tới ngày)
    df_active = df[df['Inbound Vol'].notna() | df['Outbound Vol'].notna()]
    
    t_vin = df_active['Inbound Vol'].sum()
    t_vout = df_active['Outbound Vol'].sum()
    t_win = df_active['Inbound Wgt'].sum()
    t_wout = df_active['Outbound Wgt'].sum()
    t_ms = df_active['Missort'].sum()
    t_bl = df_active['Backlog'].sum()
    
    # Tính OT MTD
    lh_total = df_active['LH Đúng Giờ'].sum() + df_active['LH Trễ'].sum()
    sh_total = df_active['Shuttle Đúng Giờ'].sum() + df_active['Shuttle Trễ'].sum()
    lhot_mtd = (df_active['LH Đúng Giờ'].sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df_active['Shuttle Đúng Giờ'].sum() / sh_total * 100) if sh_total > 0 else 0
    ms_rate_mtd = (t_ms / (t_vin + t_vout) * 100) if (t_vin + t_vout) > 0 else 0

    # Header Metrics
    cols = st.columns(4)
    cols[0].metric("Tổng Inbound (MTD)", format_vietnam(t_vin))
    cols[1].metric("Tổng Outbound (MTD)", format_vietnam(t_vout))
    cols[2].metric(f"Missort MTD ({ms_rate_mtd:.2f}%)", format_vietnam(t_ms))
    cols[3].metric("Tổng Backlog (MTD)", format_vietnam(t_bl))

    # Bảng KPI WOW
    html_table = f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th>
            </tr>
        </thead>
        <tbody>
            <tr><td rowspan="4" class="col-pillar" style="color: #0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Inbound (kg)</td>{get_wow_cell(summary['cw_win'], summary['pw_win'])}<td class="col-mtd">{format_vietnam(t_win)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td class="col-metric">Outbound (kg)</td>{get_wow_cell(summary['cw_wout'], summary['pw_wout'])}<td class="col-mtd">{format_vietnam(t_wout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color: #ef4444;">Chất Lượng</td><td class="col-metric">Tổng Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color: #10b981;">Vận Tải</td><td class="col-metric">Linehaul Đúng Giờ (%)</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.1f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.1f}%</td></tr>
        </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

    # Biểu đồ
    c_left, c_right = st.columns(2)
    with c_left:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig1.update_layout(title="Xu hướng sản lượng ngày", height=350, margin=dict(t=30, b=20, l=10, r=10))
        st.plotly_chart(fig1, use_container_width=True)
    
    with c_right:
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Đơn Missort", marker_color='#cbd5e1'), secondary_y=False)
        fig2.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", line=dict(color='#ef4444')), secondary_y=True)
        fig2.update_layout(title="Phân tích Missort", height=350, margin=dict(t=30, b=20, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("🔍 Xem dữ liệu thô"):
        st.dataframe(df.set_index("Ngày").T)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
