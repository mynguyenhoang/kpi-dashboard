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
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
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
                time.sleep(2)
                continue
        except:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals: return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v: 
                    return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return np.nan # Trả về NaN để không bị dính số 0 ảo
                return float(s)
            return np.nan
        except:
            return np.nan

    weekly_col_idxs = [3, 4, 5, 6] 
    num_days = 30 # Hiển thị full tháng

    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        # Lấy data thô và giữ nguyên NaN cho những ô chưa có dữ liệu
        cols_to_scan = [6 + i for i in range(num_days)]
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan] 
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]

        lh_c = [clean_val(lhc_idx, c) for c in cols_to_scan]
        lh_t = [clean_val(lht_idx, c) for c in cols_to_scan]
        sh_c = [clean_val(shc_idx, c) for c in cols_to_scan]
        sh_t = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        data["LH Đúng Giờ"] = [ (c - t) if pd.notna(c) else np.nan for c, t in zip(lh_c, lh_t)]
        data["LH Trễ"] = lh_t
        data["Shuttle Đúng Giờ"] = [ (c - t) if pd.notna(c) else np.nan for c, t in zip(sh_c, sh_t)]
        data["Shuttle Trễ"] = sh_t

        # LOGIC TUẦN (WOW) - Chỉ lấy cột W có số
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx))]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

        def get_ot_rate(c_idx, t_idx, col_idx):
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            return ((chuyen - (tre if pd.notna(tre) else 0)) / chuyen) * 100

        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        return pd.DataFrame(data), weekly_summary

    hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41)
    bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50)
    return hcm, bn

# 3. GIAO DIỆN HIỂN THỊ
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)

data_hcm, data_bn = get_data()
tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_num(v):
    if pd.isna(v): return "-"
    return f"{v:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) or pd.isna(prev) or prev == 0:
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{format_num(cur)}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inverse else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    
    val_str = f"{cur:.2f}%" if is_pct else format_num(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_num(prev)
    
    return f"<td style='background-color:{bg}; color:{color}; font-weight:bold; text-align:center;'>{sign}{pct:.1f}%</td><td class='col-num'>{val_str}</td><td class='col-num'>{prev_str}</td>"

def render_dashboard(df, sum, primary_color):
    # Lọc bỏ NaN để tính tổng MTD và vẽ chart
    df_clean = df.dropna(subset=['Inbound Vol'])
    
    t_vin, t_vout = df['Inbound Vol'].sum(), df['Outbound Vol'].sum()
    t_ms, t_bl = df['Missort'].sum(), df['Backlog'].sum()
    
    # Header MTD
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD)", format_num(t_vin))
    c2.metric("Tổng Outbound (MTD)", format_num(t_vout))
    c3.metric("Tổng Missort (MTD)", format_num(t_ms))
    c4.metric("Tổng Backlog (MTD)", format_num(t_bl))

    # Bảng WOW
    st.markdown(f"""
    <table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th>WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(sum['cw_vin'], sum['pw_vin'])}<td class="col-mtd">{format_num(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(sum['cw_vout'], sum['pw_vout'])}<td class="col-mtd">{format_num(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(sum['cw_ms'], sum['pw_ms'], inverse=True)}<td class="col-mtd">{format_num(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(sum['cw_bl'], sum['pw_bl'], inverse=True)}<td class="col-mtd">{format_num(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">LH Đúng Giờ (%)</td>{get_wow_cell(sum['cw_lhot'], sum['pw_lhot'], is_pct=True)}<td class="col-mtd">{df['LH Đúng Giờ'].mean():.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(sum['cw_shot'], sum['pw_shot'], is_pct=True)}<td class="col-mtd">{df['Shuttle Đúng Giờ'].mean():.2f}%</td></tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    # Biểu đồ (Sử dụng df_clean để không bị dính số 0 ảo)
    col1, col2 = st.columns(2)
    with col1:
        f1 = go.Figure()
        f1.add_trace(go.Scatter(x=df_clean['Ngày'], y=df_clean['Inbound Vol'], name="Inbound", fill='tozeroy'))
        f1.add_trace(go.Scatter(x=df_clean['Ngày'], y=df_clean['Outbound Vol'], name="Outbound", line=dict(dash='dot')))
        f1.update_layout(title="Sản lượng hàng ngày", plot_bgcolor='white', margin=dict(t=40,l=10,r=10,b=10))
        st.plotly_chart(f1, use_container_width=True)
    with col2:
        f2 = make_subplots(specs=[[{"secondary_y": True}]])
        f2.add_trace(go.Bar(x=df_clean['Ngày'], y=df_clean['Missort'], name="Missort"), secondary_y=False)
        f2.add_trace(go.Scatter(x=df_clean['Ngày'], y=df_clean['Tỷ lệ Missort (%)'], name="Tỷ lệ %", line=dict(color='red')), secondary_y=True)
        f2.update_layout(title="Chất lượng phân loại", plot_bgcolor='white')
        st.plotly_chart(f2, use_container_width=True)

    # Bảng thô chuyên nghiệp
    st.markdown("### Bảng đối soát dữ liệu thô | 原始数据")
    df_show = df.copy()
    # Định dạng hiển thị sạch sẽ
    for col in df_show.columns:
        if col != "Ngày":
            if "Tỷ lệ" in col or "Giờ" in col:
                df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
            else:
                df_show[col] = df_show[col].apply(lambda x: f"{x:,.0f}".replace(",", ".") if pd.notna(x) else "-")
    st.dataframe(df_show.set_index("Ngày").T, use_container_width=True)

with tab1: render_dashboard(data_hcm[0], data_hcm[1], "#0284c7")
with tab2: render_dashboard(data_bn[0], data_bn[1], "#059669")
