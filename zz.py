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
        line-height: 1.4;
    }
    .kpi-table td {
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        font-size: 14px;
        vertical-align: middle;
        line-height: 1.4;
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
                else: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

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
        except: return np.nan

    weekly_col_idxs = [3, 4, 5, 6] 
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
            if val.isdigit(): max_day = max(max_day, int(val))
        num_days = max_day
    else: start_col_idx = 6

    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan] 
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        lh_c_list = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_to_scan]
        lh_t_list = [clean_val(lht_idx, c) if pd.notna(clean_val(lht_idx, c)) else 0 for c in cols_to_scan]
        sh_c_list = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_to_scan]
        sh_t_list = [clean_val(sht_idx, c) if pd.notna(clean_val(sht_idx, c)) else 0 for c in cols_to_scan]
        
        data["LH Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(lh_c_list, lh_t_list)]
        data["LH Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(lh_c_list, lh_t_list)]
        data["Shuttle Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(sh_c_list, sh_t_list)]
        data["Shuttle Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(sh_c_list, sh_t_list)]

        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            return ((chuyen - (0 if pd.isna(tre) else tre)) / chuyen) * 100

        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0, "pw_vin": clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_vout": clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0, "pw_vout": clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_win": clean_val(win_idx, cw_idx) if cw_idx != -1 else 0, "pw_win": clean_val(win_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_wout": clean_val(wout_idx, cw_idx) if cw_idx != -1 else 0, "pw_wout": clean_val(wout_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_ms": clean_val(ms_idx, cw_idx) if cw_idx != -1 else 0, "pw_ms": clean_val(ms_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_bl": clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0, "pw_bl": clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), weekly_summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN HIỂN THỊ CHUNG
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu hoặc File Feishu trống...")
    st.stop()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    if diff > 0:
        bg_color, text_color, sign = "#dcfce7", "#15803d", "+"
        if inverse: bg_color, text_color = "#fee2e2", "#b91c1c"
    elif diff < 0:
        bg_color, text_color, sign = "#fee2e2", "#b91c1c", ""
        if inverse: bg_color, text_color = "#dcfce7", "#15803d"
    else: bg_color, text_color, sign = "transparent", "#333", ""
    
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    wow_td = f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'>{wow_str}</td>"
    return wow_td + f"<td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    # Tính toán các chỉ số MTD (Cả tháng)
    t_vin = df['Inbound Vol'].sum(skipna=True) 
    t_vout = df['Outbound Vol'].sum(skipna=True) 
    t_win = df['Inbound Wgt'].sum(skipna=True) 
    t_wout = df['Outbound Wgt'].sum(skipna=True) 
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    
    lh_total = df['LH Đúng Giờ'].fillna(0).sum() + df['LH Trễ'].fillna(0).sum()
    sh_total = df['Shuttle Đúng Giờ'].fillna(0).sum() + df['Shuttle Trễ'].fillna(0).sum()
    lhot_mtd = (df['LH Đúng Giờ'].fillna(0).sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df['Shuttle Đúng Giờ'].fillna(0).sum() / sh_total * 100) if sh_total > 0 else 0
    ms_rate_mtd = (t_ms / (t_vin + t_vout) * 100) if (t_vin + t_vout) > 0 else 0
    
    cw = summary
    
    # 1. HEADER METRICS (MTD) - Đã sửa lỗi logic để lấy đúng tổng tháng
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD) | 入库总量", format_vietnam(t_vin))
    c2.metric("Tổng Outbound (MTD) | 出库总量", format_vietnam(t_vout))
    c3.metric(f"Tổng Missort (MTD) | 分拣错误 ({ms_rate_mtd:.2f}%)", format_vietnam(t_ms))
    c4.metric("Tổng Backlog (MTD) | 积压货物", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. BẢNG TỔNG HỢP SONG NGỮ
    html_table = f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>KPI<br><span style='font-size:12px; font-weight:normal; color:#cbd5e1;'>关键指标</span></th>
                <th>Hạng mục<br><span style='font-size:12px; font-weight:normal; color:#cbd5e1;'>指标</span></th>
                <th style="width: 100px;">WOW<br><span style='font-size:12px; font-weight:normal; color:#cbd5e1;'>周环比</span></th>
                <th>Tuần này<br><span style='font-size:12px; font-weight:normal; color:#cbd5e1;'>本周</span></th>
                <th>Tuần trước<br><span style='font-size:12px; font-weight:normal; color:#cbd5e1;'>上周</span></th>
                <th>MTD<br><span style='font-size:12px; font-weight:normal; color:#cbd5e1;'>月度累计</span></th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="4" class="col-pillar" style="color: #0ea5e9;">Sản Lượng<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>生产</span></td>
                <td class="col-metric">Inbound (đơn)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>入境货物</span></td>
                {get_wow_cell(cw['cw_vin'], cw['pw_vin'])}
                <td class="col-mtd">{format_vietnam(t_vin)}</td>
            </tr>
            <tr>
                <td class="col-metric">Inbound (kg)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>进口重量</span></td>
                {get_wow_cell(cw['cw_win'], cw['pw_win'])}
                <td class="col-mtd">{format_vietnam(t_win)}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (đơn)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>出境货物</span></td>
                {get_wow_cell(cw['cw_vout'], cw['pw_vout'])}
                <td class="col-mtd">{format_vietnam(t_vout)}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (kg)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>出口重量</span></td>
                {get_wow_cell(cw['cw_wout'], cw['pw_wout'])}
                <td class="col-mtd">{format_vietnam(t_wout)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color: #ef4444;">Chất Lượng<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>质量</span></td>
                <td class="col-metric">Tổng Missort (đơn)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>分拣错误</span></td>
                {get_wow_cell(cw['cw_ms'], cw['pw_ms'], inverse=True)}
                <td class="col-mtd">{format_vietnam(t_ms)}</td>
            </tr>
            <tr>
                <td class="col-metric">Backlog Tồn Đọng (đơn)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>积压货物</span></td>
                {get_wow_cell(cw['cw_bl'], cw['pw_bl'], inverse=True)}
                <td class="col-mtd">{format_vietnam(t_bl)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color: #10b981;">Vận Tải<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>干线/班车</span></td>
                <td class="col-metric">Linehaul Đúng Giờ (%)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>干线准点率</span></td>
                {get_wow_cell(cw['cw_lhot'], cw['pw_lhot'], is_pct=True)}
                <td class="col-mtd">{lhot_mtd:.2f}%</td>
            </tr>
            <tr>
                <td class="col-metric">Shuttle Đúng Giờ (%)<br><span style='font-size:12px; color:#64748b; font-weight:normal;'>班车准点率</span></td>
                {get_wow_cell(cw['cw_shot'], cw['pw_shot'], is_pct=True)}
                <td class="col-mtd">{shot_mtd:.2f}%</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

    # 3. BIỂU ĐỒ
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>1. Biểu Đồ Sản Lượng & Missort | 生产与分拣图表</h4>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Sản lượng Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_vol, use_container_width=True)
    with col_chart2:
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Số đơn Missort", marker_color='#cbd5e1', opacity=0.8), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
        fig_ms.update_layout(title_text="Phân tích Missort (Số lượng & Tỷ lệ)", plot_bgcolor='white', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_ms, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>2. Quản lý Vận Tải & Hàng Tồn | 运输与积压监控</h4>", unsafe_allow_html=True)
    col_chart3, col_chart4 = st.columns(2)
    with col_chart3:
        fig_xe = go.Figure()
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['LH Đúng Giờ'].fillna(0)+df['Shuttle Đúng Giờ'].fillna(0), name="Đúng giờ COT", marker_color='#10b981'))
        fig_xe.add_trace(go.Bar(x=df['Ngày'], y=df['LH Trễ'].fillna(0)+df['Shuttle Trễ'].fillna(0), name="Trễ giờ COT", marker_color='#f43f5e'))
        fig_xe.update_layout(title="Kiểm soát Chuyến xe chạy COT (LH + Shuttle)", barmode='stack', plot_bgcolor='white', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_xe, use_container_width=True)
    with col_chart4:
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng cuối ngày")
        fig_bl.update_traces(marker_color='#f59e0b', text=[format_vietnam(v) if pd.notna(v) and v > 0 else "" for v in df['Backlog']], textposition="outside")
        fig_bl.update_layout(plot_bgcolor='white', margin=dict(t=40, l=10, r=10, b=10))
        st.plotly_chart(fig_bl, use_container_width=True)

    # 5. BẢNG DỮ LIỆU THÔ
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>3. Bảng đối soát dữ liệu thô | 原始数据</h4>", unsafe_allow_html=True)
    df_show = df.copy()
    rename_map = {
        "Inbound Vol": "Inbound (đơn) | 入境货物", "Outbound Vol": "Outbound (đơn) | 出境货物",
        "Inbound Wgt": "Inbound (kg) | 进口重量", "Outbound Wgt": "Outbound (kg) | 出口重量",
        "Missort": "Số đơn Missort | 分拣错误", "Tỷ lệ Missort (%)": "Tỷ lệ Missort (%) | 错误率",
        "Backlog": "Backlog (đơn) | 积压货物", "LH Đúng Giờ": "LH Đúng Giờ | 干线准时",
        "LH Trễ": "LH Trễ | 干线延误", "Shuttle Đúng Giờ": "Shuttle Đúng Giờ | 班车准时",
        "Shuttle Trễ": "Shuttle Trễ | 班车延误"
    }
    df_show = df_show.rename(columns=rename_map)
    for col in df_show.columns:
        if col != "Ngày":
            if "Tỷ lệ" in col: df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}%" if (pd.notna(x) and x != "") else "")
            else: df_show[col] = df_show[col].apply(format_vietnam)
    df_show = df_show.set_index("Ngày").T
    with st.expander("🔍 Bấm vào đây để xem Bảng Chi Tiết Thô Hàng Ngày | 每日原始数据", expanded=True):
        st.dataframe(df_show, use_container_width=True)

with tab1:
    render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669")
