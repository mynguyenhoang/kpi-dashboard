import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH & CSS (GIỮ NGUYÊN GIAO DIỆN BẠN THÍCH)
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; }
    .kpi-table td { padding: 10px; border: 1px solid #d1d5db; font-size: 14px; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
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
        
        def clean_val(r, c):
            try:
                v = vals[r][c]
                s = str(v).strip().replace('%', '').replace(',', '')
                if s == '' or s == '-' or '#' in s: return np.nan
                return float(s)
            except: return np.nan

        # TÌM CỘT BẮT ĐẦU (Ngày 1)
        start_col = 6
        for c in range(2, len(vals[3])):
            if str(vals[3][c]).strip() == "1":
                start_col = c
                break

        # QUAN TRỌNG: Chỉ lấy số ngày thực tế đã nhập dữ liệu (Ví dụ dựa trên HCM Inbound Vol - hàng 4)
        num_days = 0
        for i in range(31):
            val = clean_val(4, start_col + i)
            if pd.notna(val) and val > 0: num_days = i + 1
            else: break
        if num_days == 0: num_days = 26

        cols = [start_col + i for i in range(num_days)]

        def extract(vin_r, vout_r, win_r, wout_r, ms_r, ms_rt_r, bl_r, lhc_r, lht_r, shc_r, sht_r):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
            data["Inbound Vol"] = [clean_val(vin_r, c) for c in cols]
            data["Outbound Vol"] = [clean_val(vout_r, c) for c in cols]
            data["Inbound Wgt"] = [clean_val(win_r, c) for c in cols]
            data["Outbound Wgt"] = [clean_val(wout_r, c) for c in cols]
            data["Missort"] = [clean_val(ms_r, c) for c in cols]
            data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_r, c) for c in cols]
            data["Backlog"] = [clean_val(bl_r, c) for c in cols]
            
            # Xe COT
            lhc = [clean_val(lhc_r, c) or 0 for c in cols]
            lht = [clean_val(lht_r, c) or 0 for c in cols]
            shc = [clean_val(shc_r, c) or 0 for c in cols]
            sht = [clean_val(sht_r, c) or 0 for c in cols]
            data["LH Đúng Giờ"] = [(c-t) if c>0 else np.nan for c,t in zip(lhc, lht)]
            data["LH Trễ"] = [t if c>0 else np.nan for c,t in zip(lhc, lht)]
            data["Shuttle Đúng Giờ"] = [(c-t) if c>0 else np.nan for c,t in zip(shc, sht)]
            data["Shuttle Trễ"] = [t if c>0 else np.nan for c,t in zip(shc, sht)]

            # TÍNH WOW (Dựa trên cột 3,4,5,6 cố định của Feishu)
            def get_w_sum(r, c_idx): return clean_val(r, c_idx) or 0
            def get_ot(c_r, t_r, c_idx):
                c, t = clean_val(c_r, c_idx), clean_val(t_r, c_idx)
                return ((c - (t or 0))/c*100) if (c and c > 0) else 0

            # Lấy 2 tuần gần nhất có dữ liệu trong 4 cột Weekly (Cột D, E, F, G)
            w_indices = [3, 4, 5, 6]
            valid_w = [i for i in w_indices if (clean_val(vin_r, i) or 0) > 0]
            cw = valid_w[-1] if len(valid_w) >= 1 else -1
            pw = valid_w[-2] if len(valid_w) >= 2 else -1

            summary = {
                "cw_vin": get_w_sum(vin_r, cw), "pw_vin": get_w_sum(vin_r, pw),
                "cw_vout": get_w_sum(vout_r, cw), "pw_vout": get_w_sum(vout_r, pw),
                "cw_ms": get_w_sum(ms_r, cw), "pw_ms": get_w_sum(ms_r, pw),
                "cw_bl": get_w_sum(bl_r, cw), "pw_bl": get_w_sum(bl_r, pw),
                "cw_lhot": get_ot(lhc_r, lht_r, cw), "pw_lhot": get_ot(lhc_r, lht_r, pw),
                "cw_shot": get_ot(shc_r, sht_r, cw), "pw_shot": get_ot(shc_r, sht_r, pw),
            }
            return pd.DataFrame(data), summary

        df_hcm, s_hcm = extract(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
        df_bn, s_bn = extract(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
        return (df_hcm, s_hcm), (df_bn, s_bn)
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

# 3. GIAO DIỆN
(df_hcm, sum_hcm), (df_bn, sum_bn) = get_data()

def format_vn(n):
    if pd.isna(n) or n == "": return ""
    return f"{n:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if not prev or prev == 0:
        return f"<td style='text-align:center;'>-</td><td class='col-num'>{f'{cur:.2f}%' if is_pct else format_vn(cur)}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    # Đảo ngược màu nếu là Missort/Backlog (tăng là đỏ)
    is_good = diff < 0 if inverse else diff > 0
    color, bg = ("#15803d", "#dcfce7") if is_good else ("#b91c1c", "#fee2e2")
    if diff == 0: color, bg = "#333", "transparent"
    
    sign = "+" if diff > 0 else ""
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{wow_str}</td>" + \
           f"<td class='col-num'>{f'{cur:.2f}%' if is_pct else format_vn(cur)}</td>" + \
           f"<td class='col-num'>{f'{prev:.2f}%' if is_pct else format_vn(prev)}</td>"

def render(df, s, color):
    if df.empty: return
    # MTD chuẩn: Sum() chỉ trên những ngày có dữ liệu thực tế
    mtd_vin = df['Inbound Vol'].sum()
    mtd_vout = df['Outbound Vol'].sum()
    mtd_ms = df['Missort'].sum()
    mtd_bl = df['Backlog'].iloc[-1] # Lấy tồn kho ngày cuối cùng
    
    lh_mtd = (df['LH Đúng Giờ'].sum() / (df['LH Đúng Giờ'].sum() + df['LH Trễ'].sum()) * 100) if (df['LH Đúng Giờ'].sum() + df['LH Trễ'].sum()) > 0 else 0
    sh_mtd = (df['Shuttle Đúng Giờ'].sum() / (df['Shuttle Đúng Giờ'].sum() + df['Shuttle Trễ'].sum()) * 100) if (df['Shuttle Đúng Giờ'].sum() + df['Shuttle Trễ'].sum()) > 0 else 0

    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:80px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar" style="color:{color}">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(s['cw_vin'], s['pw_vin'])}<td class="col-mtd">{format_vn(mtd_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(s['cw_vout'], s['pw_vout'])}<td class="col-mtd">{format_vn(mtd_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(s['cw_ms'], s['pw_ms'], inverse=True)}<td class="col-mtd">{format_vn(mtd_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(s['cw_bl'], s['pw_bl'], inverse=True)}<td class="col-mtd">{format_vn(mtd_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981">Vận Tải</td><td class="col-metric">Linehaul (%)</td>{get_wow_cell(s['cw_lhot'], s['pw_lhot'], is_pct=True)}<td class="col-mtd">{lh_mtd:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle (%)</td>{get_wow_cell(s['cw_shot'], s['pw_shot'], is_pct=True)}<td class="col-mtd">{sh_mtd:.2f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)
    
    # BIỂU ĐỒ (Giữ nguyên)
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color=color)))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.bar(df, x="Ngày", y="Backlog", title="Hàng tồn (Backlog)", color_discrete_sequence=['#f59e0b'])
        st.plotly_chart(fig2, use_container_width=True)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1: render(df_hcm, sum_hcm, "#0284c7")
with tab2: render(df_bn, sum_bn, "#059669")
