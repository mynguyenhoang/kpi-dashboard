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
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-table th { background-color: #1f2937; color: white; padding: 10px 12px; text-align: center; border: 1px solid #d1d5db; font-size: 14px; font-weight: bold; }
    .kpi-table td { padding: 10px 12px; border: 1px solid #d1d5db; font-size: 14px; vertical-align: middle; }
    .col-pillar { font-weight: bold; text-align: center; background-color: #f8fafc; }
    .col-metric { font-weight: 600; color: #1e293b; }
    .col-num { text-align: right; font-family: monospace; font-size: 15px; }
    .col-mtd { text-align: right; font-family: monospace; font-size: 15px; font-weight: bold; background-color: #f0fdf4; }
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU (Giữ nguyên logic của ông)
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

    def clean_val(r, c):
        try:
            v = vals[r][c]
            s = str(v).replace('%', '').replace(',', '').strip()
            return float(s) if s not in ["", "-", "None"] else np.nan
        except: return np.nan

    num_days = 26 
    start_col_idx = 6 # Giả định cột bắt đầu từ G

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        cols = [start_col_idx + i for i in range(num_days)]
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols]
        data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols]
        data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols]
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols]
        data["LH Đúng Giờ"] = [clean_val(lhc_idx, c) - clean_val(lht_idx, c) for c in cols]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols]
        data["Shuttle Đúng Giờ"] = [clean_val(shc_idx, c) - clean_val(sht_idx, c) for c in cols]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols]
        
        # Fake weekly summary for demo
        summary = {"cw_vin": 100, "pw_vin": 90, "cw_vout": 100, "pw_vout": 90, "cw_ms": 5, "pw_ms": 6, "cw_bl": 10, "pw_bl": 12, "cw_lhot": 90, "pw_lhot": 85, "cw_shot": 95, "pw_shot": 90}
        return pd.DataFrame(data), summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. RENDER DASHBOARD
def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    st.markdown(f"<h4 style='color: {primary_color};'>1. Biểu Đồ Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    
    with col1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', 
                                     mode='lines+text', 
                                     text=[format_vietnam(v) if v > 5000 else "" for v in df['Inbound Vol']], 
                                     textfont=dict(size=13, color='black', family="Arial Black"),
                                     textposition="top center", line=dict(color='#0ea5e9')))
        fig_vol.update_layout(title="Inbound Vol hàng ngày", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_vol, use_container_width=True)

    # ĐOẠN NÀY LÀ CHỈNH SỐ BỰ CHO NĂNG SUẤT
    with col2:
        fig_prod_v = go.Figure()
        fig_prod_v.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#38bdf8',
                                    text=[format_vietnam(v) for v in df['Total Process Vol']], 
                                    textposition='outside',
                                    textfont=dict(size=14, color='#1e293b', family="Arial Black"))) # Chỉnh size 14, font đậm
        fig_prod_v.add_hline(y=df['Total Process Vol'].mean(), line_dash="dash", line_color="red")
        fig_prod_v.update_layout(title="Năng suất (Số đơn)", plot_bgcolor='white', yaxis=dict(range=[0, df['Total Process Vol'].max()*1.15])) # Tăng range để không mất số
        st.plotly_chart(fig_prod_v, use_container_width=True)

    with col3:
        fig_prod_w = go.Figure()
        fig_prod_w.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#818cf8',
                                    text=[format_vietnam(v) for v in df['Total Process Wgt']], 
                                    textposition='outside',
                                    textfont=dict(size=14, color='#1e293b', family="Arial Black"))) # Chỉnh size 14, font đậm
        fig_prod_w.add_hline(y=df['Total Process Wgt'].mean(), line_dash="dash", line_color="red")
        fig_prod_w.update_layout(title="Năng suất (Trọng lượng kg)", plot_bgcolor='white', yaxis=dict(range=[0, df['Total Process Wgt'].max()*1.15]))
        st.plotly_chart(fig_prod_w, use_container_width=True)

    st.markdown(f"<h4 style='color: {primary_color};'>2. Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    
    with c4:
        fig_lh = go.Figure()
        fig_lh.add_trace(go.Bar(x=df['Ngày'], y=df['LH Đúng Giờ'], name="Đúng", marker_color='#10b981', 
                                text=df['LH Đúng Giờ'], textposition='inside', textfont=dict(size=12, color='white', family="Arial Black")))
        fig_lh.add_trace(go.Bar(x=df['Ngày'], y=df['LH Trễ'], name="Trễ", marker_color='#f43f5e', 
                                text=df['LH Trễ'], textposition='inside', textfont=dict(size=12, color='white', family="Arial Black")))
        fig_lh.update_layout(title="Linehaul", barmode='stack', plot_bgcolor='white')
        st.plotly_chart(fig_lh, use_container_width=True)

    with c5:
        fig_sh = go.Figure()
        fig_sh.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Đúng Giờ'], name="Đúng", marker_color='#10b981', 
                                text=df['Shuttle Đúng Giờ'], textposition='inside', textfont=dict(size=12, color='white', family="Arial Black")))
        fig_sh.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Trễ'], name="Trễ", marker_color='#f43f5e', 
                                text=df['Shuttle Trễ'], textposition='inside', textfont=dict(size=12, color='white', family="Arial Black")))
        fig_sh.update_layout(title="Shuttle", barmode='stack', plot_bgcolor='white')
        st.plotly_chart(fig_sh, use_container_width=True)

    with c6:
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", 
                        text=df['Backlog'].apply(lambda x: format_vietnam(x) if x > 0 else ""))
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside', textfont=dict(size=14, family="Arial Black"))
        fig_bl.update_layout(plot_bgcolor='white', yaxis=dict(range=[0, df['Backlog'].max()*1.2]))
        st.plotly_chart(fig_bl, use_container_width=True)

# MAIN
data_hcm, data_bn = get_data()
tab1, tab2 = st.tabs(["HCM", "BẮC NINH"])
with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
