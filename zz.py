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
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
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
    
    res_data = None
    for _ in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            time.sleep(2)
        except: continue

    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if not v or str_v == "" or "#" in str_v or "IF(" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else np.nan
            return np.nan
        except: return np.nan

    weekly_cols = [3, 4, 5, 6] 

    def extract_hub_data(vin, vout, win, wout, ms, msr, bl, lhc, lht, shc, sht):
        cols = [6 + i for i in range(30)]
        data = {"Ngày": [f"Ngày {i+1}" for i in range(30)]}
        data["Inbound Vol"] = [clean_val(vin, c) for c in cols]
        data["Outbound Vol"] = [clean_val(vout, c) for c in cols]
        data["Inbound Wgt"] = [clean_val(win, c) for c in cols]
        data["Outbound Wgt"] = [clean_val(wout, c) for c in cols]
        data["Missort"] = [clean_val(ms, c) for c in cols]
        data["Tỷ lệ Missort (%)"] = [clean_val(msr, c) for c in cols] 
        data["Backlog"] = [clean_val(bl, c) for c in cols]
        
        lh_c = [clean_val(lhc, c) for c in cols]; lh_t = [clean_val(lht, c) for c in cols]
        sh_c = [clean_val(shc, c) for c in cols]; sh_t = [clean_val(sht, c) for c in cols]
        
        data["LH Đúng Giờ"] = [(c - t) if pd.notna(c) else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = lh_t
        data["Shuttle Đúng Giờ"] = [(c - t) if pd.notna(c) else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = sh_t

        valid_ws = [idx for idx in weekly_cols if pd.notna(clean_val(vin, idx))]
        cw_idx = valid_ws[-1] if valid_ws else -1
        pw_idx = valid_ws[-2] if len(valid_ws) > 1 else -1

        def calc_ot(c_idx, t_idx, col):
            if col == -1: return 0
            ch, tr = clean_val(c_idx, col), clean_val(t_idx, col)
            return ((ch - (tr if pd.notna(tr) else 0)) / ch * 100) if ch and ch > 0 else 0

        summary = {
            "cw_vin": clean_val(vin, cw_idx), "pw_vin": clean_val(vin, pw_idx),
            "cw_vout": clean_val(vout, cw_idx), "pw_vout": clean_val(vout, pw_idx),
            "cw_win": clean_val(win, cw_idx), "pw_win": clean_val(win, pw_idx),
            "cw_wout": clean_val(wout, cw_idx), "pw_wout": clean_val(wout, pw_idx),
            "cw_ms": clean_val(ms, cw_idx), "pw_ms": clean_val(ms, pw_idx),
            "cw_bl": clean_val(bl, cw_idx), "pw_bl": clean_val(bl, pw_idx),
            "cw_lhot": calc_ot(lhc, lht, cw_idx), "pw_lhot": calc_ot(lhc, lht, pw_idx),
            "cw_shot": calc_ot(shc, sht, cw_idx), "pw_shot": calc_ot(shc, sht, pw_idx),
        }
        return pd.DataFrame(data), summary

    hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return hcm, bn

# 3. GIAO DIỆN HIỂN THỊ
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 20px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def fmt(v): return f"{v:,.0f}".replace(",", ".") if pd.notna(v) else "-"

def get_cell(cur, prev, is_pct=False, inv=False):
    if pd.isna(cur) or pd.isna(prev) or prev == 0:
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{fmt(cur)}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    color = "#15803d" if (diff > 0 if not inv else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inv else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{sign}{pct:.1f}%</td><td class='col-num'>{cur:.2f}%" if is_pct else f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{sign}{pct:.1f}%</td><td class='col-num'>{fmt(cur)}</td><td class='col-num'>{fmt(prev)}</td>"

def render_dashboard(df, sm, color):
    df_c = df.dropna(subset=['Inbound Vol'])
    t_vin, t_vout = df['Inbound Vol'].sum(), df['Outbound Vol'].sum()
    t_ms, t_bl = df['Missort'].sum(), df['Backlog'].sum()
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", fmt(t_vin))
    c2.metric("Tổng Outbound (MTD)", fmt(t_vout))
    c3.metric("Tổng Missort (MTD)", fmt(t_ms))
    c4.metric("Tổng Backlog (MTD)", fmt(t_bl))

    # Bảng KPI
    st.markdown(f"""
    <table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:100px">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_cell(sm['cw_vin'], sm['pw_vin'])}<td class="col-mtd">{fmt(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_cell(sm['cw_vout'], sm['pw_vout'])}<td class="col-mtd">{fmt(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_cell(sm['cw_ms'], sm['pw_ms'], inv=True)}<td class="col-mtd">{fmt(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_cell(sm['cw_bl'], sm['pw_bl'], inv=True)}<td class="col-mtd">{fmt(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">LH Đúng Giờ (%)</td>{get_cell(sm['cw_lhot'], sm['pw_lhot'], True)}<td class="col-mtd">{df['LH Đúng Giờ'].mean():.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_cell(sm['cw_shot'], sm['pw_shot'], True)}<td class="col-mtd">{df['Shuttle Đúng Giờ'].mean():.2f}%</td></tr>
        </tbody>
    </table>""", unsafe_allow_html=True)

    # Charts
    cl1, cl2 = st.columns(2)
    with cl1:
        f1 = go.Figure()
        f1.add_trace(go.Scatter(x=df_c['Ngày'], y=df_c['Inbound Vol'], name="Inbound", fill='tozeroy'))
        f1.add_trace(go.Scatter(x=df_c['Ngày'], y=df_c['Outbound Vol'], name="Outbound", line=dict(dash='dot')))
        f1.update_layout(title="Sản lượng hàng ngày", plot_bgcolor='white', margin=dict(t=40,l=10,r=10,b=10))
        st.plotly_chart(f1, use_container_width=True)
    with cl2:
        f2 = make_subplots(specs=[[{"secondary_y": True}]])
        f2.add_trace(go.Bar(x=df_c['Ngày'], y=df_c['Missort'], name="Missort"), secondary_y=False)
        f2.add_trace(go.Scatter(x=df_c['Ngày'], y=df_c['Tỷ lệ Missort (%)'], name="Tỷ lệ %", line=dict(color='red')), secondary_y=True)
        f2.update_layout(title="Chất lượng phân loại", plot_bgcolor='white')
        st.plotly_chart(f2, use_container_width=True)

    # BẢNG THÔ LÔI RA NGOÀI (KHÔNG CẮT BỚT)
    st.markdown("#### 3. Bảng đối soát dữ liệu thô | 原始数据")
    df_show = df.copy()
    rename_map = {"Inbound Vol": "In Vol", "Outbound Vol": "Out Vol", "Inbound Wgt": "In Wgt", "Outbound Wgt": "Out Wgt", "Missort": "Missort", "Tỷ lệ Missort (%)": "Missort %", "Backlog": "Backlog", "LH Đúng Giờ": "LH OK", "LH Trễ": "LH Late", "Shuttle Đúng Giờ": "Shuttle OK", "Shuttle Trễ": "Shuttle Late"}
    df_show = df_show.rename(columns=rename_map)
    for col in df_show.columns:
        if col != "Ngày":
            if "%" in col or "OK" in col: df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
            else: df_show[col] = df_show[col].apply(lambda x: fmt(x))
    st.dataframe(df_show.set_index("Ngày").T, use_container_width=True)

with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
