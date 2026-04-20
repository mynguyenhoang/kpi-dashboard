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
st.markdown("""<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 15px 20px; border-radius: 8px; }
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except: return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
        if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

        def clean_val(row_idx, col_idx):
            try:
                if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                    v = vals[row_idx][col_idx]
                    str_v = str(v).strip()
                    if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v: return np.nan
                    s = str_v.replace('%', '').replace(',', '').strip()
                    return float(s) if s != '-' else 0.0
                return np.nan
            except: return np.nan

        # Logic tìm ngày bắt đầu và kết thúc thực tế
        start_col = 6
        for c in range(2, len(vals[3])):
            if str(vals[3][c]).strip() == "1":
                start_col = c
                break
        
        # Đếm số ngày thực tế có dữ liệu Inbound (Hàng 4 cho HCM, Hàng 10 cho BN)
        actual_days = 0
        for i in range(31):
            if pd.notna(clean_val(4, start_col + i)) or pd.notna(clean_val(10, start_col + i)):
                actual_days = i + 1
            else: break
        
        num_days = actual_days if actual_days > 0 else 26
        cols_to_scan = [start_col + i for i in range(num_days)]
        weekly_cols = [3, 4, 5, 6]

        def extract_hub(vin, vout, win, wout, ms, ms_rt, bl, lhc, lht, shc, sht):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
            data["Inbound Vol"] = [clean_val(vin, c) for c in cols_to_scan]
            data["Outbound Vol"] = [clean_val(vout, c) for c in cols_to_scan]
            data["Inbound Wgt"] = [clean_val(win, c) for c in cols_to_scan]
            data["Outbound Wgt"] = [clean_val(wout, c) for c in cols_to_scan]
            data["Missort"] = [clean_val(ms, c) for c in cols_to_scan]
            data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt, c) for c in cols_to_scan]
            data["Backlog"] = [clean_val(bl, c) for c in cols_to_scan]
            
            # Logic Vận tải
            lh_c = [clean_val(lhc, c) or 0 for c in cols_to_scan]
            lh_t = [clean_val(lht, c) or 0 for c in cols_to_scan]
            sh_c = [clean_val(shc, c) or 0 for c in cols_to_scan]
            sh_t = [clean_val(sht, c) or 0 for c in cols_to_scan]
            data["LH Đúng Giờ"] = [(c-t) if c>0 else np.nan for c,t in zip(lh_c, lh_t)]
            data["LH Trễ"] = [t if c>0 else np.nan for c,t in zip(lh_c, lh_t)]
            data["Shuttle Đúng Giờ"] = [(c-t) if c>0 else np.nan for c,t in zip(sh_c, sh_t)]
            data["Shuttle Trễ"] = [t if c>0 else np.nan for c,t in zip(sh_c, sh_t)]

            # WOW Summary
            valid_w = [idx for idx in weekly_cols if pd.notna(clean_val(vin, idx)) and clean_val(vin, idx) > 0]
            cw_idx = valid_w[-1] if len(valid_w) >= 1 else -1
            pw_idx = valid_w[-2] if len(valid_w) >= 2 else -1

            def get_ot_rate(c_idx, t_idx, col_idx):
                if col_idx == -1: return 0
                c, t = clean_val(c_idx, col_idx), clean_val(t_idx, col_idx)
                return ((c - (t or 0)) / c * 100) if (c and c > 0) else 0

            summary = {
                "cw_vin": clean_val(vin, cw_idx), "pw_vin": clean_val(vin, pw_idx),
                "cw_vout": clean_val(vout, cw_idx), "pw_vout": clean_val(vout, pw_idx),
                "cw_win": clean_val(win, cw_idx), "pw_win": clean_val(win, pw_idx),
                "cw_wout": clean_val(wout, cw_idx), "pw_wout": clean_val(wout, pw_idx),
                "cw_ms": clean_val(ms, cw_idx), "pw_ms": clean_val(ms, pw_idx),
                "cw_bl": clean_val(bl, cw_idx), "pw_bl": clean_val(bl, pw_idx),
                "cw_lhot": get_ot_rate(lhc, lht, cw_idx), "pw_lhot": get_ot_rate(lhc, lht, pw_idx),
                "cw_shot": get_ot_rate(shc, sht, cw_idx), "pw_shot": get_ot_rate(shc, sht, pw_idx),
            }
            return pd.DataFrame(data), summary

        data_hcm = extract_hub(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
        data_bn = extract_hub(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
        return data_hcm, data_bn
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

# 3. HIỂN THỊ
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
(df_hcm, sum_hcm), (df_bn, sum_bn) = get_data()

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or prev == 0:
        val = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{val}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inverse else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{wow_str}</td>" + \
           f"<td class='col-num'>{f'{cur:.2f}%' if is_pct else format_vietnam(cur)}</td>" + \
           f"<td class='col-num'>{f'{prev:.2f}%' if is_pct else format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    # MTD logic: sum() bây giờ chỉ cộng đến ngày có dữ liệu thực tế
    t_vin, t_vout = df['Inbound Vol'].sum(), df['Outbound Vol'].sum()
    t_win, t_wout = df['Inbound Wgt'].sum(), df['Outbound Wgt'].sum()
    t_ms, t_bl = df['Missort'].sum(), df['Backlog'].iloc[-1] # Backlog lấy ngày mới nhất
    
    lh_ok = df['LH Đúng Giờ'].sum()
    lh_total = lh_ok + df['LH Trễ'].sum()
    lhot_mtd = (lh_ok / lh_total * 100) if lh_total > 0 else 0
    
    sh_ok = df['Shuttle Đúng Giờ'].sum()
    sh_total = sh_ok + df['Shuttle Trễ'].sum()
    shot_mtd = (sh_ok / sh_total * 100) if sh_total > 0 else 0

    # Metrics top
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Tổng Outbound (MTD)", format_vietnam(t_vout))
    c3.metric(f"Tổng Missort (MTD)", format_vietnam(t_ms), f"{(t_ms/(t_vin+t_vout)*100):.2f}%" if (t_vin+t_vout)>0 else "0%")
    c4.metric("Backlog (Hiện tại)", format_vietnam(t_bl))

    # Bảng WOW/MTD
    html = f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:80px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">Linehaul (%)</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle (%)</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td></tr>
        </tbody></table>"""
    st.markdown(html, unsafe_allow_html=True)

    # Biểu đồ
    c_l, c_r = st.columns(2)
    with c_l:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color=primary_color)))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Sản lượng hàng ngày", margin=dict(t=40, b=10))
        st.plotly_chart(fig_vol, use_container_width=True)
    with c_r:
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Missort", marker_color='#cbd5e1'), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="%", line=dict(color='#ef4444')), secondary_y=True)
        fig_ms.update_layout(title="Phân tích Missort", margin=dict(t=40, b=10))
        st.plotly_chart(fig_ms, use_container_width=True)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2: render_dashboard(df_bn, sum_bn, "#059669")
