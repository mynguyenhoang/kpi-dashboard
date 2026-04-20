import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS TÙY CHỈNH
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; }
    .kpi-table th { background-color: #1e293b; color: #f8fafc; padding: 14px 16px; text-align: center; border: 1px solid #cbd5e1; font-size: 16px; font-weight: 700; }
    .kpi-table td { padding: 12px 16px; border: 1px solid #cbd5e1; font-size: 15px; vertical-align: middle; }
    .col-pillar { font-weight: 800; text-align: center; background-color: #f8fafc; font-size: 16px; }
    .col-metric { font-weight: 600; color: #334155; }
    .col-num { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 16px; font-weight: 600;}
    .col-mtd { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 17px; font-weight: 800; background-color: #f0fdf4; color: #166534; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.04); transition: transform 0.2s ease-in-out; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    .main-title { text-align: center; font-weight: 900; color: #0f172a; font-size: 42px; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 1.5px; }
</style>""", unsafe_allow_html=True)

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
    if not token:
        st.error("Không lấy được Token Feishu.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        if res.get("code") != 0: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = str(vals[row_idx][col_idx]).strip()
                if v == "" or v == "-" or "None" in v: return 0.0
                s = v.replace('%', '').replace(',', '').strip()
                return float(s)
            return 0.0
        except: return 0.0

    # Lấy ngày hiện tại để giới hạn chart
    start_col = 6
    num_days = 26
    cols = [start_col + i for i in range(num_days)]

    def extract_hub_data(vin_r, vout_r, tpv_r, tpw_r, ms_r, bl_r, cot_t_r, cot_o_r, shc_r, sht_r, lhc_r, lht_r):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_r, c) for c in cols]
        data["Outbound Vol"] = [clean_val(vout_r, c) for c in cols]
        data["Total Process Vol"] = [clean_val(tpv_r, c) for c in cols]
        data["Total Process Wgt"] = [clean_val(tpw_r, c) for c in cols]
        data["Missort"] = [clean_val(ms_r, c) for c in cols]
        data["Backlog"] = [clean_val(bl_r, c) for c in cols]
        
        # Dữ liệu COT
        data["COT Total"] = [clean_val(cot_t_r, c) for c in cols]
        data["COT Ontime"] = [clean_val(cot_o_r, c) for c in cols]
        data["COT Rate (%)"] = [(o/t*100) if t > 0 else 0 for t, o in zip(data["COT Total"], data["COT Ontime"])]
        data["COT Late Rate (%)"] = [(1 - (o/t))*100 if t > 0 else 0 for t, o in zip(data["COT Total"], data["COT Ontime"])]

        # Dữ liệu Vận tải
        data["Shuttle Chuyến"] = [clean_val(shc_r, c) for c in cols]
        data["Shuttle Late"] = [clean_val(sht_r, c) for c in cols]
        data["Linehaul Chuyến"] = [clean_val(lhc_r, c) for c in cols]
        data["Linehaul Late"] = [clean_val(lht_r, c) for c in cols]
        data["LH Sai Giờ (%)"] = [(l/c*100) if c > 0 else 0 for c, l in zip(data["Linehaul Chuyến"], data["Linehaul Late"])]
        data["Shuttle Sai Giờ (%)"] = [(l/c*100) if c > 0 else 0 for c, l in zip(data["Shuttle Chuyến"], data["Shuttle Late"])]

        # Logic Tuần này (Cột 3) vs Tuần trước (Cột 4)
        cw, pw = 3, 4
        summary = {
            "cw_vin": clean_val(vin_r, cw), "pw_vin": clean_val(vin_r, pw),
            "cw_vout": clean_val(vout_r, cw), "pw_vout": clean_val(vout_r, pw),
            "cw_tpw": clean_val(tpw_r, cw), "pw_tpw": clean_val(tpw_r, pw),
            "cw_ms": clean_val(ms_r, cw), "pw_ms": clean_val(ms_r, pw),
            "cw_bl": clean_val(bl_r, cw), "pw_bl": clean_val(bl_r, pw),
            "cw_cot_late": (1 - (clean_val(cot_o_r, cw)/clean_val(cot_t_r, cw)))*100 if clean_val(cot_t_r, cw) > 0 else 0,
            "pw_cot_late": (1 - (clean_val(cot_o_r, pw)/clean_val(cot_t_r, pw)))*100 if clean_val(cot_t_r, pw) > 0 else 0,
            "cw_lh_late": (clean_val(lht_r, cw)/clean_val(lhc_r, cw)*100) if clean_val(lhc_r, cw) > 0 else 0,
            "pw_lh_late": (clean_val(lht_r, pw)/clean_val(lhc_r, pw)*100) if clean_val(lhc_r, pw) > 0 else 0,
            "cw_sh_late": (clean_val(sht_r, cw)/clean_val(shc_r, cw)*100) if clean_val(shc_r, cw) > 0 else 0,
            "pw_sh_late": (clean_val(sht_r, pw)/clean_val(shc_r, pw)*100) if clean_val(shc_r, pw) > 0 else 0,
        }
        return pd.DataFrame(data), summary

    # HCM INDEX FIX (Rà soát lại index dòng trên sheet Feishu)
    df_hcm, sum_hcm = extract_hub_data(4, 5, 8, 9, 17, 31, 35, 36, 38, 40, 39, 41)
    # BN INDEX FIX (Rà soát lại index dòng tương ứng)
    df_bn, sum_bn = extract_hub_data(10, 11, 14, 15, 19, 32, 44, 45, 47, 49, 48, 50)
    
    return (df_hcm, sum_hcm), (df_bn, sum_bn)

# 3. UI RENDERING
def format_num(n):
    return f"{n:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=True):
    # inverse=True: Tăng là Đỏ (Late Rate, Missort)
    if prev == 0: return f"<td>-</td><td class='col-num'>{cur:.1f}%</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff/prev*100)
    color = "#fee2e2" if diff > 0 else "#dcfce7"
    text_c = "#b91c1c" if diff > 0 else "#15803d"
    sign = "+" if diff > 0 else ""
    val_disp = f"{cur:.1f}%" if is_pct else format_num(cur)
    prev_disp = f"{prev:.1f}%" if is_pct else format_num(prev)
    return f"<td style='background-color:{color}; color:{text_c}; font-weight:bold; text-align:center;'>{sign}{pct:.1f}%</td><td class='col-num'>{val_disp}</td><td class='col-num'>{prev_disp}</td>"

def render_dashboard(df, summary, primary_color):
    # Bảng WOW
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:110px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="3" class="col-pillar" style="color:#0ea5e9;">Sản Lượng | 生产</td><td class="col-metric">Inbound (đơn) | 入库单量</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'], inverse=False)}<td class="col-mtd">{format_num(df['Inbound Vol'].sum())}</td></tr>
            <tr><td class="col-metric">Outbound (đơn) | 出库单量</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'], inverse=False)}<td class="col-mtd">{format_num(df['Outbound Vol'].sum())}</td></tr>
            <tr><td class="col-metric">Trọng lượng (kg) | 重量 kg</td>{get_wow_cell(summary['cw_tpw'], summary['pw_tpw'], inverse=False)}<td class="col-mtd">{format_num(df['Total Process Wgt'].sum())}</td></tr>
            <tr><td rowspan="3" class="col-pillar" style="color:#ef4444;">Chất Lượng | 质量</td><td class="col-metric">Missort (đơn) | 错分单量</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'])}<td class="col-mtd">{format_num(df['Missort'].sum())}</td></tr>
            <tr><td class="col-metric">Backlog (đơn) | 积压单量</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'])}<td class="col-mtd">{format_num(df['Backlog'].sum())}</td></tr>
            <tr><td class="col-metric">% Delay COT | 延误出库率 %</td>{get_wow_cell(summary['cw_cot_late'], summary['pw_cot_late'], is_pct=True)}<td class="col-mtd">{(1 - df['COT Ontime'].sum()/df['COT Total'].sum())*100:.1f}%</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải | 运输</td><td class="col-metric">LH Sai Giờ (%) | 干线延迟率</td>{get_wow_cell(summary['cw_lh_late'], summary['pw_lh_late'], is_pct=True)}<td class="col-mtd">{(df['Linehaul Late'].sum()/df['Linehaul Chuyến'].sum()*100) if df['Linehaul Chuyến'].sum() > 0 else 0:.1f}%</td></tr>
            <tr><td class="col-metric">Shuttle Sai Giờ (%) | 支线延迟率</td>{get_wow_cell(summary['cw_sh_late'], summary['pw_sh_late'], is_pct=True)}<td class="col-mtd">{(df['Shuttle Late'].sum()/df['Shuttle Chuyến'].sum()*100) if df['Shuttle Chuyến'].sum() > 0 else 0:.1f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # Dòng biểu đồ Năng suất
    st.markdown("<h3 style='font-size: 20px;'>1. Sản Lượng & Năng Suất</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], name="Đơn xử lý", marker_color='#38bdf8', text=[format_num(x) if x>0 else "" for x in df['Total Process Vol']], textposition='outside'))
        fig.add_trace(go.Scatter(x=df['Ngày'], y=df['Total Process Vol'], name="Xu hướng", line=dict(color='#ef4444', width=3, shape='spline')))
        fig.update_layout(plot_bgcolor='white', height=400, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig_cot = go.Figure()
        fig_cot.add_trace(go.Bar(x=df['Ngày'], y=df['COT Ontime'], name="Đơn đạt COT", marker_color='#10b981', text=[format_num(x) if x>0 else "" for x in df['COT Ontime']], textposition='outside'))
        fig_cot.add_trace(go.Scatter(x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ đúng %", yaxis="y2", line=dict(color='#ef4444', width=3)))
        fig_cot.update_layout(plot_bgcolor='white', height=400, yaxis2=dict(overlaying='y', side='right', range=[0, 110]), margin=dict(t=30, b=10))
        st.plotly_chart(fig_cot, use_container_width=True)

    # Dòng trễ xe & Backlog
    st.markdown("<h3 style='font-size: 20px;'>2. Vận Tải & Hàng Tồn</h3>", unsafe_allow_html=True)
    c3, c4, c5 = st.columns(3)
    with c3:
        fig_sh = go.Figure(go.Bar(x=df['Ngày'], y=df['Shuttle Late'], marker_color='#ef4444', text=[int(x) if x>0 else "" for x in df['Shuttle Late']], textposition='outside'))
        fig_sh.update_layout(title="Shuttle Sai Giờ", plot_bgcolor='white', height=300)
        st.plotly_chart(fig_sh, use_container_width=True)
    with c4:
        fig_lh = go.Figure(go.Bar(x=df['Ngày'], y=df['Linehaul Late'], marker_color='#f43f5e', text=[int(x) if x>0 else "" for x in df['Linehaul Late']], textposition='outside'))
        fig_lh.update_layout(title="Linehaul Sai Giờ", plot_bgcolor='white', height=300)
        st.plotly_chart(fig_lh, use_container_width=True)
    with c5:
        fig_bl = go.Figure(go.Bar(x=df['Ngày'], y=df['Backlog'], marker_color='#f59e0b', text=[format_num(x) if x>0 else "" for x in df['Backlog']], textposition='outside'))
        fig_bl.update_layout(title="Backlog tích trữ", plot_bgcolor='white', height=300)
        st.plotly_chart(fig_bl, use_container_width=True)

# MAIN APP
hcm, bn = get_data()
tab_hcm, tab_bn = st.tabs(["📌 HỒ CHÍ MINH", "📌 BẮC NINH"])
with tab_hcm: render_dashboard(hcm[0], hcm[1], "#0284c7")
with tab_bn: render_dashboard(bn[0], bn[1], "#059669")
