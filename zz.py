import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# 1. CẤU HÌNH TRANG & CSS
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .kpi-table th { background-color: #1e293b; color: #f8fafc; padding: 14px 16px; text-align: center; border: 1px solid #cbd5e1; font-weight: 700; }
    .kpi-table td { padding: 12px 16px; border: 1px solid #cbd5e1; font-size: 15px; }
    .col-pillar { font-weight: 800; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #334155; }
    .col-num { text-align: right; font-family: 'Courier New', monospace; font-weight: 600;}
    .col-mtd { text-align: right; font-family: 'Courier New', monospace; font-weight: 800; background-color: #f0fdf4; color: #166534; }
    .main-title { text-align: center; font-weight: 900; color: #0f172a; font-size: 42px; margin-bottom: 40px; text-transform: uppercase; }
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU (Giữ nguyên logic Feishu của ông)
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
    
    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            v = vals[row_idx][col_idx]
            s = str(v).replace('%', '').replace(',', '').strip()
            return float(s) if s not in ["", "-", "None", "nan"] else 0.0
        except: return 0.0

    start_col_idx = 6 # Giả định cột bắt đầu dữ liệu ngày 1
    num_days = 26
    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin, vout, win, wout, tp_v, tp_w, ms, ms_r, bl, shc, sht, lhc, lht, cot_t, cot_o):
        data = {
            "Ngày": [f"{i+1}" for i in range(num_days)],
            "Inbound Vol": [clean_val(vin, c) for c in cols_to_scan],
            "Outbound Vol": [clean_val(vout, c) for c in cols_to_scan],
            "Total Process Wgt": [clean_val(tp_w, c) for c in cols_to_scan],
            "Missort": [clean_val(ms, c) for c in cols_to_scan],
            "Backlog": [clean_val(bl, c) for c in cols_to_scan],
            "COT Ontime": [clean_val(cot_o, c) for c in cols_to_scan],
            "COT Total": [clean_val(cot_t, c) for c in cols_to_scan],
            "Shuttle Chuyến": [clean_val(shc, c) for c in cols_to_scan],
            "Linehaul Chuyến": [clean_val(lhc, c) for c in cols_to_scan],
            "Shuttle Late": [clean_val(sht, c) for c in cols_to_scan],
            "Linehaul Late": [clean_val(lht, c) for c in cols_to_scan]
        }
        df = pd.DataFrame(data)
        df["COT Rate (%)"] = (df["COT Ontime"] / df["COT Total"] * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Logic tính WOW (Tuần này vs Tuần trước - Giả định 4 cột đầu là tuần)
        cw, pw = 3, 4 # Index cột tuần trên sheet
        summary = {
            "cw_vin": clean_val(vin, cw), "pw_vin": clean_val(vin, pw),
            "cw_vout": clean_val(vout, cw), "pw_vout": clean_val(vout, pw),
            "cw_tp_w": clean_val(tp_w, cw), "pw_tp_w": clean_val(tp_w, pw),
            "cw_ms": clean_val(ms, cw), "pw_ms": clean_val(ms, pw),
            "cw_bl": clean_val(bl, cw), "pw_bl": clean_val(bl, pw),
            "cw_cot_late": (1 - (clean_val(cot_o, cw)/clean_val(cot_t, cw)))*100 if clean_val(cot_t, cw) > 0 else 0,
            "pw_cot_late": (1 - (clean_val(cot_o, pw)/clean_val(cot_t, pw)))*100 if clean_val(cot_t, pw) > 0 else 0,
            "cw_lh_late": (clean_val(lht, cw)/clean_val(lhc, cw)*100) if clean_val(lhc, cw) > 0 else 0,
            "pw_lh_late": (clean_val(lht, pw)/clean_val(lhc, pw)*100) if clean_val(lhc, pw) > 0 else 0,
            "cw_sh_late": (clean_val(sht, cw)/clean_val(shc, cw)*100) if clean_val(shc, cw) > 0 else 0,
            "pw_sh_late": (clean_val(sht, pw)/clean_val(shc, pw)*100) if clean_val(shc, pw) > 0 else 0,
        }
        return df, summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41, 35, 36)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50, 44, 45)
    return data_hcm, data_bn

# 3. GIAO DIỆN
st.markdown("<div class='main-title'>J&T CARGO KPI DASHBOARD</div>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()

def format_num(n):
    return f"{n:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=True):
    # Inverse=True: Tăng là Đỏ (dành cho các chỉ số LỖI/TRỄ)
    if prev == 0: return f"<td>-</td><td class='col-num'>{cur:.1f}%</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff/prev*100)
    color = "#fee2e2" if diff > 0 else "#dcfce7"
    text_c = "#b91c1c" if diff > 0 else "#15803d"
    sign = "+" if diff > 0 else ""
    val_display = f"{cur:.1f}%" if is_pct else format_num(cur)
    prev_display = f"{prev:.1f}%" if is_pct else format_num(prev)
    return f"<td style='background-color:{color}; color:{text_c}; font-weight:bold; text-align:center;'>{sign}{pct:.1f}%</td><td class='col-num'>{val_display}</td><td class='col-num'>{prev_display}</td>"

def render_tab(df, sum, color):
    # Bảng WOW - Đã sửa tên "LH Trễ Giờ" và "Shuttle Trễ Giờ"
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="3" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(sum['cw_vin'], sum['pw_vin'], inverse=False)}<td class="col-mtd">{format_num(df['Inbound Vol'].sum())}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(sum['cw_vout'], sum['pw_vout'], inverse=False)}<td class="col-mtd">{format_num(df['Outbound Vol'].sum())}</td></tr>
            <tr><td class="col-metric">Trọng lượng (kg)</td>{get_wow_cell(sum['cw_tp_w'], sum['pw_tp_w'], inverse=False)}<td class="col-mtd">{format_num(df['Total Process Wgt'].sum())}</td></tr>
            <tr><td rowspan="3" class="col-pillar" style="color:#ef4444;">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(sum['cw_ms'], sum['pw_ms'])}<td class="col-mtd">{format_num(df['Missort'].sum())}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(sum['cw_bl'], sum['pw_bl'])}<td class="col-mtd">{format_num(df['Backlog'].sum())}</td></tr>
            <tr><td class="col-metric">% Delay COT</td>{get_wow_cell(sum['cw_cot_late'], sum['pw_cot_late'], is_pct=True)}<td class="col-mtd">-</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td><td class="col-metric">LH Trễ Giờ (%)</td>{get_wow_cell(sum['cw_lh_late'], sum['pw_lh_late'], is_pct=True)}<td class="col-mtd">-</td></tr>
            <tr><td class="col-metric">Shuttle Trễ Giờ (%)</td>{get_wow_cell(sum['cw_sh_late'], sum['pw_sh_late'], is_pct=True)}<td class="col-mtd">-</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # Chart COT - Đã bỏ Tổng đơn, chỉ giữ Đơn đạt COT và hiện số
    fig_cot = go.Figure()
    fig_cot.add_trace(go.Bar(
        x=df['Ngày'], y=df['COT Ontime'], 
        name="Đơn đạt COT", 
        marker_color='#10b981',
        text=[format_num(x) if x > 0 else "" for x in df['COT Ontime']],
        textposition='outside', # Hiển thị số trên đầu cột
        textfont=dict(size=12, color='#166534', fontWeight='bold')
    ))
    fig_cot.add_trace(go.Scatter(
        x=df['Ngày'], y=df['COT Rate (%)'], 
        name="Tỷ lệ đúng (%)", 
        yaxis="y2", 
        line=dict(color='#ef4444', width=3),
        mode='lines+markers'
    ))
    fig_cot.update_layout(
        title="<b>Volume Ontime COT & Tỷ lệ đúng hàng ngày</b>",
        yaxis=dict(title="Số đơn hàng"),
        yaxis2=dict(title="Tỷ lệ (%)", overlaying='y', side='right', range=[0, 110]),
        plot_bgcolor='white', height=500, margin=dict(t=50, b=50),
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig_cot, use_container_width=True)

tab1, tab2 = st.tabs(["📌 HỒ CHÍ MINH", "📌 BẮC NINH"])
with tab1: render_tab(data_hcm[0], data_hcm[1], "#0284c7")
with tab2: render_tab(data_bn[0], data_bn[1], "#059669")
