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
    
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        if res.get("code") != 0: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        vals = res.get('data', {}).get('valueRange', {}).get('values', [])
    except:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not vals or len(vals) < 50:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return float(s) if s != '-' else 0.0
            return np.nan
        except:
            return np.nan

    # Xác định vị trí cột Ngày (Thường bắt đầu từ cột index 6)
    start_col_idx = 7 # Điều chỉnh theo cấu trúc thực tế của bạn
    num_days = 31 
    weekly_col_idxs = [3, 4, 5, 6] # Các cột WOW cố định

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        # CHỈ quét các cột từ Ngày 1 đến Ngày 31, bỏ qua các cột summary trong sheet
        day_cols = []
        for c in range(start_col_idx, start_col_idx + num_days):
            if c < len(vals[3]): # Dòng 3 thường chứa tiêu đề ngày
                day_cols.append(c)

        data_rows = []
        for i, c_idx in enumerate(day_cols):
            # Nếu ngày đó hoàn toàn không có dữ liệu Inbound/Outbound thì bỏ qua để MTD không sai
            v_in = clean_val(vin_idx, c_idx)
            v_out = clean_val(vout_idx, c_idx)
            
            row = {
                "Ngày": f"Ngày {i+1}",
                "Inbound Vol": v_in,
                "Outbound Vol": v_out,
                "Inbound Wgt": clean_val(win_idx, c_idx),
                "Outbound Wgt": clean_val(wout_idx, c_idx),
                "Missort": clean_val(ms_idx, c_idx),
                "Tỷ lệ Missort (%)": clean_val(ms_rt_idx, c_idx),
                "Backlog": clean_val(bl_idx, c_idx),
                "LH_C": clean_val(lhc_idx, c_idx),
                "LH_T": clean_val(lht_idx, c_idx),
                "SH_C": clean_val(shc_idx, c_idx),
                "SH_T": clean_val(sht_idx, c_idx)
            }
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Tính toán cột bổ trợ cho chart
        df["LH Đúng Giờ"] = df["LH_C"] - df["LH_T"].fillna(0)
        df["LH Trễ"] = df["LH_T"]
        df["Shuttle Đúng Giờ"] = df["SH_C"] - df["SH_T"].fillna(0)
        df["Shuttle Trễ"] = df["SH_T"]

        # Lấy dữ liệu Weekly (WOW) từ các cột cố định
        cw_idx, pw_idx = weekly_col_idxs[-1], weekly_col_idxs[-2]
        
        def get_ot_rate(c_idx, t_idx, col_idx):
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            return ((chuyen - tre) / chuyen * 100) if (chuyen and chuyen > 0) else 0

        summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return df, summary

    data_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    data_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return data_hcm, data_bn

# 3. GIAO DIỆN HIỂN THỊ
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()

def format_vietnam(number):
    if pd.isna(number): return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(prev) or prev == 0:
        val = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align:center;'>-</td><td class='col-num'>{val}</td><td class='col-num'>-</td>"
    
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inverse else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{wow_str}</td><td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return

    # TÍNH TOÁN MTD CHUẨN (Chỉ sum các giá trị hợp lệ trong tháng)
    t_vin = df['Inbound Vol'].sum(skipna=True)
    t_vout = df['Outbound Vol'].sum(skipna=True)
    t_win = df['Inbound Wgt'].sum(skipna=True)
    t_wout = df['Outbound Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    # Backlog lấy giá trị cuối cùng có dữ liệu (không cộng dồn)
    valid_bl = df['Backlog'].dropna()
    t_bl = valid_bl.iloc[-1] if not valid_bl.empty else 0
    
    ms_rate_mtd = (t_ms / (t_vin + t_vout) * 100) if (t_vin + t_vout) > 0 else 0
    
    lh_total = df['LH_C'].sum()
    sh_total = df['SH_C'].sum()
    lhot_mtd = ((lh_total - df['LH_T'].sum()) / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = ((sh_total - df['SH_T'].sum()) / sh_total * 100) if sh_total > 0 else 0

    # 1. HEADER METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Tổng Outbound (MTD)", format_vietnam(t_vout))
    c3.metric(f"Tổng Missort ({ms_rate_mtd:.2f}%)", format_vietnam(t_ms))
    c4.metric("Backlog Hiện Tại", format_vietnam(t_bl))

    # 2. BẢNG TỔNG HỢP
    html_table = f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="4" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td>
                <td class="col-metric">Inbound (đơn)</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td>
            </tr>
            <tr>
                <td class="col-metric">Inbound (kg)</td>{get_wow_cell(summary['cw_win'], summary['pw_win'])}<td class="col-mtd">{format_vietnam(t_win)}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (đơn)</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (kg)</td>{get_wow_cell(summary['cw_wout'], summary['pw_wout'])}<td class="col-mtd">{format_vietnam(t_wout)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td>
                <td class="col-metric">Missort (đơn)</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td>
            </tr>
            <tr>
                <td class="col-metric">Backlog (đơn)</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td>
                <td class="col-metric">Linehaul Đúng Giờ (%)</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td>
            </tr>
            <tr>
                <td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)

    # 3. BIỂU ĐỒ (Giữ nguyên logic cũ của bạn)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Sản lượng Inbound & Outbound hàng ngày", plot_bgcolor='white', height=350)
        st.plotly_chart(fig_vol, use_container_width=True)
    with col_chart2:
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Số đơn Missort", marker_color='#cbd5e1'), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", line=dict(color='#ef4444')), secondary_y=True)
        fig_ms.update_layout(title="Phân tích Missort hàng ngày", plot_bgcolor='white', height=350)
        st.plotly_chart(fig_ms, use_container_width=True)

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])
with tab1:
    render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with tab2:
    render_dashboard(data_bn[0], data_bn[1], "#059669")
