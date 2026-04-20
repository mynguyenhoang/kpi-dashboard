import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# 1. CẤU HÌNH TRANG & CSS
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px; text-align: center; border: 1px solid #d1d5db; font-size: 13px; }
    .kpi-table td { padding: 10px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; }
    .col-mtd { text-align: right; font-family: monospace; font-weight: bold; background-color: #f0fdf4; }
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
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not vals or len(vals) < 50: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip()
                if not v or v in ["None", "", "-", "#VALUE!", "#N/A"]: return np.nan
                return float(v.replace('%', '').replace(',', ''))
            return np.nan
        except: return np.nan

    # Lấy tiêu đề ngày để xác định dải cột (Từ cột G trở đi)
    start_col = 6
    num_days = 31 # Giới hạn tối đa 31 ngày để tránh lọt vào cột Tổng MTD của Feishu
    
    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        day_labels = []
        data_list = []
        for i in range(num_days):
            col_idx = start_col + i
            # Nếu gặp cột "Total" hoặc cột trống ở dòng ngày tháng thì dừng
            day_val = str(vals[3][col_idx]).strip() if col_idx < len(vals[3]) else ""
            if not day_val or not day_val.isdigit(): break
            
            day_labels.append(f"Ngày {day_val}")
            data_list.append({
                "Inbound Vol": clean_val(vin_idx, col_idx),
                "Outbound Vol": clean_val(vout_idx, col_idx),
                "Inbound Wgt": clean_val(win_idx, col_idx),
                "Outbound Wgt": clean_val(wout_idx, col_idx),
                "Missort": clean_val(ms_idx, col_idx),
                "Tỷ lệ Missort (%)": clean_val(ms_rt_idx, col_idx),
                "Backlog": clean_val(bl_idx, col_idx),
                "LH_C": clean_val(lhc_idx, col_idx),
                "LH_T": clean_val(lht_idx, col_idx),
                "SH_C": clean_val(shc_idx, col_idx),
                "SH_T": clean_val(sht_idx, col_idx)
            })
        
        df = pd.DataFrame(data_list)
        df.insert(0, "Ngày", day_labels)
        
        # Xử lý Vận tải
        df["LH Đúng Giờ"] = df["LH_C"] - df["LH_T"].fillna(0)
        df["LH Trễ"] = df["LH_T"]
        df["Shuttle Đúng Giờ"] = df["SH_C"] - df["SH_T"].fillna(0)
        df["Shuttle Trễ"] = df["SH_T"]

        # Weekly Summary (Cột D, E, F)
        weekly_idxs = [3, 4, 5] # Tuần 1, 2, 3...
        cw_idx = -1
        for idx in reversed(weekly_idxs):
            if not pd.isna(clean_val(vin_idx, idx)):
                cw_idx = idx
                break
        pw_idx = cw_idx - 1 if cw_idx > 3 else -1

        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": ((clean_val(lhc_idx, cw_idx) - clean_val(lht_idx, cw_idx))/clean_val(lhc_idx, cw_idx)*100) if clean_val(lhc_idx, cw_idx) else 0,
            "pw_lhot": ((clean_val(lhc_idx, pw_idx) - clean_val(lht_idx, pw_idx))/clean_val(lhc_idx, pw_idx)*100) if clean_val(lhc_idx, pw_idx) else 0,
            "cw_shot": ((clean_val(shc_idx, cw_idx) - clean_val(sht_idx, cw_idx))/clean_val(shc_idx, cw_idx)*100) if clean_val(shc_idx, cw_idx) else 0,
            "pw_shot": ((clean_val(shc_idx, pw_idx) - clean_val(sht_idx, pw_idx))/clean_val(shc_idx, pw_idx)*100) if clean_val(shc_idx, pw_idx) else 0,
        }
        return df, summary

    df_hcm, s_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    df_bn, s_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return (df_hcm, s_hcm), (df_bn, s_bn)

# 3. HIỂN THỊ
st.markdown("<h2 style='text-align: center; color: #1e293b;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
(df_hcm, sum_hcm), (df_bn, sum_bn) = get_data()

def format_num(v):
    if pd.isna(v) or v == "": return ""
    return f"{v:,.0f}".replace(",", ".")

def get_wow_td(cur, prev, is_pct=False, inverse=False):
    cur = cur or 0
    prev = prev or 0
    diff = (cur - prev) if is_pct else (((cur - prev)/prev*100) if prev != 0 else 0)
    color = "#15803d" if (diff > 0 and not inverse) or (diff < 0 and inverse) else "#b91c1c"
    if abs(diff) < 0.1: color = "#333"
    sign = "+" if diff > 0 else ""
    return f"<td style='color:{color}; font-weight:bold; text-align:center;'>{sign}{diff:.0f}%</td><td class='col-num'>{'%.1f%%'%cur if is_pct else format_num(cur)}</td><td class='col-num'>{'%.1f%%'%prev if is_pct else format_num(prev)}</td>"

def render(df, s):
    if df.empty: 
        st.error("Không có dữ liệu hiển thị.")
        return
    
    # MTD Calculation - Chỉ sum những dòng thực sự có dữ liệu
    df_mtd = df.dropna(subset=['Inbound Vol'])
    m_vin, m_vout = df_mtd['Inbound Vol'].sum(), df_mtd['Outbound Vol'].sum()
    m_win, m_wout = df_mtd['Inbound Wgt'].sum(), df_mtd['Outbound Wgt'].sum()
    m_ms, m_bl = df_mtd['Missort'].sum(), df_mtd['Backlog'].sum()
    
    # OT MTD
    lh_total = df_mtd['LH_C'].sum()
    sh_total = df_mtd['SH_C'].sum()
    m_lhot = ((lh_total - df_mtd['LH_T'].sum()) / lh_total * 100) if lh_total > 0 else 0
    m_shot = ((sh_total - df_mtd['SH_T'].sum()) / sh_total * 100) if sh_total > 0 else 0

    c = st.columns(4)
    c[0].metric("Inbound MTD", format_num(m_vin))
    c[1].metric("Outbound MTD", format_num(m_vout))
    c[2].metric("Missort MTD", format_num(m_ms))
    c[3].metric("Backlog MTD", format_num(m_bl))

    st.markdown(f"""
    <table class="kpi-table">
        <tr><th>Nhóm</th><th>Chỉ số</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr>
        <tr><td rowspan="2" class="col-pillar">Sản lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_td(s['cw_vin'], s['pw_vin'])}<td class="col-mtd">{format_num(m_vin)}</td></tr>
        <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_td(s['cw_vout'], s['pw_vout'])}<td class="col-mtd">{format_num(m_vout)}</td></tr>
        <tr><td rowspan="2" class="col-pillar">Chất lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_td(s['cw_ms'], s['pw_ms'], inverse=True)}<td class="col-mtd">{format_num(m_ms)}</td></tr>
        <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_td(s['cw_bl'], s['pw_bl'], inverse=True)}<td class="col-mtd">{format_num(m_bl)}</td></tr>
        <tr><td rowspan="2" class="col-pillar">Vận tải</td><td class="col-metric">Linehaul OT%</td>{get_wow_td(s['cw_lhot'], s['pw_lhot'], is_pct=True)}<td class="col-mtd">{m_lhot:.1f}%</td></tr>
        <tr><td class="col-metric">Shuttle OT%</td>{get_wow_td(s['cw_shot'], s['pw_shot'], is_pct=True)}<td class="col-mtd">{m_shot:.1f}%</td></tr>
    </table>
    """, unsafe_allow_html=True)

    # Charts
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Sản lượng", "Chất lượng"))
    fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy'), row=1, col=1)
    fig.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Missort"), row=1, col=2)
    fig.update_layout(height=400, margin=dict(t=50, b=20, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

t1, t2 = st.tabs(["HỒ CHÍ MINH", "BẮC NINH"])
with t1: render(df_hcm, sum_hcm)
with t2: render(df_bn, sum_bn)
