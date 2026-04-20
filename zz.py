import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="metric-container"] > div > div > div > div:first-child {
        color: #64748b;
        font-weight: 600;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
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
        return pd.DataFrame(), pd.DataFrame()

    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    
    max_retries = 3
    res_data = None
    
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            elif "not ready" in str(res.get("msg")).lower():
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    st.error(f"Lỗi Feishu: {res.get('msg')} (File tính toán quá lâu)")
                    return pd.DataFrame(), pd.DataFrame()
            else:
                st.error(f"Lỗi Feishu: {res.get('msg')}")
                return pd.DataFrame(), pd.DataFrame()
        except Exception as e:
            st.error(f"Lỗi kết nối: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    if not res_data:
        return pd.DataFrame(), pd.DataFrame()

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55:
        return pd.DataFrame(), pd.DataFrame()

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v: 
                    return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except:
            return np.nan

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

    def extract_hub_data(vol_idx, wgt_idx, ms_idx, ms_rt_idx, fte_idx, bl_idx, chuyen_idxs, tre_idxs, lh_rt_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Tổng lượng hàng"] = [clean_val(vol_idx, c) for c in cols_to_scan]
        data["Tổng trọng lượng (Kg)"] = [clean_val(wgt_idx, c) for c in cols_to_scan]
        data["Số đơn Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan]
        data["Tổng nhân sự"] = [clean_val(fte_idx, c) for c in cols_to_scan]
        data["Backlog tồn đọng"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Linehaul đúng giờ (%)"] = [clean_val(lh_rt_idx, c) for c in cols_to_scan]

        xe_sai_list = []
        xe_dung_list = []
        for c in cols_to_scan:
            chuyen_vals = [clean_val(r, c) for r in chuyen_idxs]
            tre_vals = [clean_val(r, c) for r in tre_idxs]
            sum_chuyen = sum([x for x in chuyen_vals if pd.notna(x)])
            sum_tre = sum([x for x in tre_vals if pd.notna(x)])
            
            if sum_chuyen == 0 and all(pd.isna(x) for x in chuyen_vals):
                xe_sai_list.append(np.nan)
                xe_dung_list.append(np.nan)
            else:
                xe_sai_list.append(sum_tre)
                xe_dung_list.append(sum_chuyen - sum_tre)
                
        data["Xe Sai COT (Tổng)"] = xe_sai_list
        data["Xe Đúng COT (Tổng)"] = xe_dung_list
        return pd.DataFrame(data)

    df_hcm = extract_hub_data(8, 9, 17, 18, 23, 31, [38, 39], [40, 41], 43)
    df_bn = extract_hub_data(14, 15, 19, 20, 26, 32, [47, 48], [49, 50], 52)
    return df_hcm, df_bn

# 3. GIAO DIỆN HIỂN THỊ CHUNG
st.markdown("<h2 style='text-align: center; font-weight: 700; color: #1e293b; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
df_hcm, df_bn = get_data()

if df_hcm.empty and df_bn.empty:
    st.warning("Không tìm thấy dữ liệu. Vui lòng kiểm tra lại file Feishu.")
    st.stop()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vietnam(number):
    if pd.isna(number): return "0"
    return f"{number:,.0f}".replace(",", ".")

def render_dashboard(df, primary_color):
    if df.empty:
        st.info("Chưa có dữ liệu cho Hub này.")
        return

    # TÍNH TỔNG MTD
    total_vol = df['Tổng lượng hàng'].sum(skipna=True) 
    total_weight = df['Tổng trọng lượng (Kg)'].sum(skipna=True)
    total_missort = df['Số đơn Missort'].sum(skipna=True)
    total_backlog = df['Backlog tồn đọng'].sum(skipna=True)

    total_xe_dung = df['Xe Đúng COT (Tổng)'].sum(skipna=True)
    total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum(skipna=True)
    final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0
    final_missort_rate = (total_missort / total_vol * 100) if total_vol > 0 else 0

    # TÍNH WOW (LINH HOẠT THEO SỐ NGÀY HIỆN CÓ)
    valid_df = df.dropna(subset=['Tổng lượng hàng'])
    delta_vol = delta_wgt = delta_ms = delta_bl = delta_ot = None 
    
    n_days = len(valid_df)
    if n_days >= 4:
        period = min(7, n_days // 2) 
        cw = valid_df.iloc[-period:]
        pw = valid_df.iloc[-(2*period):-period]
        
        def calc_wow(cur, prev):
            return ((cur - prev) / prev * 100) if prev > 0 else 0.0

        delta_vol = f"{calc_wow(cw['Tổng lượng hàng'].sum(), pw['Tổng lượng hàng'].sum()):.1f}% WoW"
        delta_wgt = f"{calc_wow(cw['Tổng trọng lượng (Kg)'].sum(), pw['Tổng trọng lượng (Kg)'].sum()):.1f}% WoW"
        delta_ms = f"{calc_wow(cw['Số đơn Missort'].sum(), pw['Số đơn Missort'].sum()):.1f}% WoW"
        delta_bl = f"{calc_wow(cw['Backlog tồn đọng'].sum(), pw['Backlog tồn đọng'].sum()):.1f}% WoW"
        
        cw_xe_chay = cw['Xe Đúng COT (Tổng)'].sum() + cw['Xe Sai COT (Tổng)'].sum()
        cw_ot = (cw['Xe Đúng COT (Tổng)'].sum() / cw_xe_chay * 100) if cw_xe_chay > 0 else 0
        pw_xe_chay = pw['Xe Đúng COT (Tổng)'].sum() + pw['Xe Sai COT (Tổng)'].sum()
        pw_ot = (pw['Xe Đúng COT (Tổng)'].sum() / pw_xe_chay * 100) if pw_xe_chay > 0 else 0
        delta_ot = f"{(cw_ot - pw_ot):.1f}% WoW"

    # AUTO ALERTS
    recent_3_days = valid_df.iloc[-3:]
    alerts = []
    for index, row in recent_3_days.iterrows():
        if pd.notna(row['Backlog tồn đọng']) and row['Backlog tồn đọng'] > 100:
            alerts.append(f"Ngày {row['Ngày']}: Tồn đọng (Backlog) cao bất thường ({format_vietnam(row['Backlog tồn đọng'])} đơn).")
        if pd.notna(row['Số đơn Missort']) and row['Số đơn Missort'] > 50:
            alerts.append(f"Ngày {row['Ngày']}: Missort tăng đột biến ({format_vietnam(row['Số đơn Missort'])} đơn).")
    
    if alerts:
        with st.expander("HỆ THỐNG CẢNH BÁO VẬN HÀNH NGẮN HẠN", expanded=True):
            for alert in alerts:
                st.error(alert)

    # HEADER METRICS
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tổng Sản Lượng", format_vietnam(total_vol), delta=delta_vol)
    c2.metric("Tổng Trọng Lượng", format_vietnam(total_weight) + " kg", delta=delta_wgt)
    c3.metric(f"Tổng Missort ({final_missort_rate:.2f}%)", format_vietnam(total_missort), delta=delta_ms, delta_color="inverse")
    c4.metric("Tổng Backlog", format_vietnam(total_backlog), delta=delta_bl, delta_color="inverse")
    c5.metric("Tỷ Lệ LH Đúng Giờ", f"{final_ontime_rate:.2f}%", delta=delta_ot)

    st.markdown("<br>", unsafe_allow_html=True)

    # CHARTS
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>1. Đánh giá Sản Lượng & Chất Lượng Phân Loại (Missort)</h4>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_vol = px.area(df, x="Ngày", y="Tổng lượng hàng", title="Biểu đồ Sản lượng hàng ngày")
        fig_vol.update_traces(line_color=primary_color, fillcolor='rgba(56, 189, 248, 0.2)', mode='lines+markers+text', 
                              text=[format_vietnam(v) if pd.notna(v) else "" for v in df['Tổng lượng hàng']], textposition="top center")
        fig_vol.update_layout(plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10))
        fig_vol.update_xaxes(showgrid=False)
        fig_vol.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_chart2:
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Số đơn Missort'], name="Số đơn Missort", marker_color='#cbd5e1', opacity=0.8), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
        fig_ms.update_layout(title_text="Phân tích Missort (Số lượng & Tỷ lệ)", plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_ms.update_xaxes(showgrid=False)
        fig_ms.update_yaxes(showgrid=True, gridcolor='#f1f5f9', secondary_y=False)
        st.plotly_chart(fig_ms, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>2. Quản lý Vận Tải (Linehaul) & Hàng Tồn (Backlog)</h4>", unsafe_allow_html=True)
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        fig_xe = go.Figure()
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['Xe Đúng COT (Tổng)'], name="Đúng giờ COT", marker_color='#10b981'))
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['Xe Sai COT (Tổng)'], name="Trễ giờ COT", marker_color='#f43f5e'))
        fig_xe.update_layout(title="Kiểm soát Chuyến xe chạy COT", barmode='stack', plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_xe.update_xaxes(showgrid=False)
        fig_xe.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_xe, use_container_width=True)

    with col_chart4:
        fig_bl = px.bar(df, x="Ngày", y="Backlog tồn đọng", title="Backlog tồn đọng cuối ngày")
        fig_bl.update_traces(marker_color='#f59e0b', text=[format_vietnam(v) if pd.notna(v) and v > 0 else "" for v in df['Backlog tồn đọng']], textposition="outside")
        fig_bl.update_layout(plot_bgcolor='white', hovermode='x unified', margin=dict(t=40, l=10, r=10, b=10))
        fig_bl.update_xaxes(showgrid=False)
        fig_bl.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
        st.plotly_chart(fig_bl, use_container_width=True)

    with st.expander("Bảng đối soát dữ liệu thô (Bấm để xem)"):
        df_show = df.copy()
        for col in df_show.columns:
            if col != "Ngày":
                df_show[col] = df_show[col].apply(lambda x: format_vietnam(x) if pd.notna(x) else "")
        df_show = df_show.set_index("Ngày").T
        st.dataframe(df_show, use_container_width=True)

with tab1:
    render_dashboard(df_hcm, primary_color="#0284c7") 
with tab2:
    render_dashboard(df_bn, primary_color="#059669")
