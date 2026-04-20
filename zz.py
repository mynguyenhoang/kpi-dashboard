import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS CHO BẢNG MỚI
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Style cho bảng số liệu tổng hợp y chang file Excel */
    .kpi-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
        background-color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kpi-table th {
        background-color: #1f2937; /* Màu xám đen giống header Excel */
        color: white;
        padding: 12px;
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

def get_wow_cell(cur, prev, is_pct=False):
    """Hàm tạo mã HTML cho 3 cột: WoW, Kỳ Này, Kỳ Trước y chang Excel"""
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"

    if is_pct:
        diff = cur - prev
        pct = diff
    else:
        diff = cur - prev
        pct = (diff / prev) * 100 if prev > 0 else 0

    # Logic màu chuẩn Trung Quốc (Red = Tăng, Green = Giảm)
    if diff > 0:
        bg_color = "#fecaca" # Nền đỏ nhạt
        text_color = "#dc2626" # Chữ đỏ đậm
        sign = "+"
    elif diff < 0:
        bg_color = "#bbf7d0" # Nền xanh nhạt
        text_color = "#16a34a" # Chữ xanh đậm
        sign = ""
    else:
        bg_color = "transparent"
        text_color = "#333"
        sign = ""
        
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)

    wow_td = f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'>{wow_str}</td>"
    cur_td = f"<td class='col-num'>{cur_str}</td>"
    prev_td = f"<td class='col-num'>{prev_str}</td>"

    return wow_td + cur_td + prev_td

def render_dashboard(df, primary_color):
    if df.empty:
        st.info("Chưa có dữ liệu cho Hub này.")
        return

    # TÍNH TỔNG (MTD)
    total_vol = df['Tổng lượng hàng'].sum(skipna=True) 
    total_weight = df['Tổng trọng lượng (Kg)'].sum(skipna=True)
    total_missort = df['Số đơn Missort'].sum(skipna=True)
    total_backlog = df['Backlog tồn đọng'].sum(skipna=True)

    total_xe_dung = df['Xe Đúng COT (Tổng)'].sum(skipna=True)
    total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum(skipna=True)
    final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0

    # TÍNH DATA 2 KỲ (Tuần này / Tuần trước)
    valid_df = df.dropna(subset=['Tổng lượng hàng'])
    cw_vol = cw_wgt = cw_ms = cw_bl = cw_ot = 0
    pw_vol = pw_wgt = pw_ms = pw_bl = pw_ot = None
    
    n_days = len(valid_df)
    if n_days >= 4:
        period = min(7, n_days // 2) 
        cw = valid_df.iloc[-period:]
        pw = valid_df.iloc[-(2*period):-period]
        
        cw_vol, pw_vol = cw['Tổng lượng hàng'].sum(), pw['Tổng lượng hàng'].sum()
        cw_wgt, pw_wgt = cw['Tổng trọng lượng (Kg)'].sum(), pw['Tổng trọng lượng (Kg)'].sum()
        cw_ms, pw_ms = cw['Số đơn Missort'].sum(), pw['Số đơn Missort'].sum()
        cw_bl, pw_bl = cw['Backlog tồn đọng'].sum(), pw['Backlog tồn đọng'].sum()
        
        cw_xe_chay = cw['Xe Đúng COT (Tổng)'].sum() + cw['Xe Sai COT (Tổng)'].sum()
        cw_ot = (cw['Xe Đúng COT (Tổng)'].sum() / cw_xe_chay * 100) if cw_xe_chay > 0 else 0
        pw_xe_chay = pw['Xe Đúng COT (Tổng)'].sum() + pw['Xe Sai COT (Tổng)'].sum()
        pw_ot = (pw['Xe Đúng COT (Tổng)'].sum() / pw_xe_chay * 100) if pw_xe_chay > 0 else 0

    # HIỂN THỊ BẢNG TỔNG HỢP (THAY THẾ HOÀN TOÀN ST.METRIC BẰNG BẢNG HTML)
    html_table = f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>Pillar (Nhóm)</th>
                <th>Metrics (Chỉ tiêu)</th>
                <th style="width: 100px;">WoW</th>
                <th>Kỳ Này (Current)</th>
                <th>Kỳ Trước (Previous)</th>
                <th>Tổng Tháng (MTD)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="2" class="col-pillar" style="color: #0ea5e9;">Inbound<br>(Sản Lượng)</td>
                <td class="col-metric">Tổng Sản Lượng (đơn)</td>
                {get_wow_cell(cw_vol, pw_vol)}
                <td class="col-mtd">{format_vietnam(total_vol)}</td>
            </tr>
            <tr>
                <td class="col-metric">Tổng Trọng Lượng (kg)</td>
                {get_wow_cell(cw_wgt, pw_wgt)}
                <td class="col-mtd">{format_vietnam(total_weight)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color: #ef4444;">Quality<br>(Chất Lượng)</td>
                <td class="col-metric">Tổng Missort (đơn)</td>
                {get_wow_cell(cw_ms, pw_ms)}
                <td class="col-mtd">{format_vietnam(total_missort)}</td>
            </tr>
            <tr>
                <td class="col-metric">Backlog Tồn Đọng (đơn)</td>
                {get_wow_cell(cw_bl, pw_bl)}
                <td class="col-mtd">{format_vietnam(total_backlog)}</td>
            </tr>
            <tr>
                <td class="col-pillar" style="color: #10b981;">Linehaul<br>(Vận Tải)</td>
                <td class="col-metric">Tỷ Lệ Đúng Giờ (%)</td>
                {get_wow_cell(cw_ot, pw_ot, is_pct=True)}
                <td class="col-mtd">{final_ontime_rate:.2f}%</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

    # KHU VỰC VẼ BIỂU ĐỒ (Giữ nguyên)
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>1. Biểu Đồ Sản Lượng & Chất Lượng Phân Loại</h4>", unsafe_allow_html=True)
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

    # Đưa hẳn bảng số liệu thô ra ngoài
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>3. Bảng đối soát dữ liệu thô</h4>", unsafe_allow_html=True)
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
