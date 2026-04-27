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
    /* --- ÉP CHẾ ĐỘ NỀN SÁNG (LIGHT MODE) CỐ ĐỊNH --- */
    .stApp, [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; }
    
    /* Chỉnh màu chữ cho các Tab */
    button[data-baseweb="tab"] div { color: #1e3a8a !important; font-weight: bold !important; }
    
    /* --- ĐỊNH DẠNG BẢNG & GIAO DIỆN CHÍNH --- */
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; }
    .kpi-table th { background-color: #1e3a8a !important; color: #ffffff !important; padding: 14px 10px; text-align: center; border: 1px solid #94a3b8; font-size: 16px; font-weight: 800; }
    .kpi-table td { padding: 12px 10px; border: 1px solid #cbd5e1; font-size: 16px; vertical-align: middle; color: #1e293b; }
    .col-pillar { font-weight: 800; text-align: center; background-color: #f1f5f9 !important; font-size: 17px; }
    .col-metric { font-weight: 700; color: #0f172a !important; }
    .col-num { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 17px; font-weight: 700; }
    .col-mtd { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 19px; font-weight: 900; background-color: #dcfce7 !important; color: #166534 !important; }
    
    /* --- ĐỊNH DẠNG 6 Ô METRIC TRÊN CÙNG --- */
    div[data-testid="metric-container"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08); transition: transform 0.2s ease-in-out; border-left: 5px solid #2563eb; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.15); }
    div[data-testid="metric-container"] label { font-size: 17px !important; font-weight: 700 !important; color: #334155 !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 36px !important; font-weight: 900 !important; color: #1e3a8a !important; }
    .main-title { text-align: center; font-weight: 900; color: #0f172a !important; font-size: 46px; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
    
    /* --- ẨN NÚT GITHUB, MENU ĐỂ BẢO VỆ CHẤT XÁM --- */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
</style>""", unsafe_allow_html=True)

# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU 
def get_tenant_access_token():
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": "cli_a9456e412bb89bce", "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"}
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except Exception as e: 
        st.error(f"🔴 Lỗi lấy Token Feishu: {str(e)}")
        return None

@st.cache_data(ttl=60) 
def get_data():
    token = get_tenant_access_token()
    if not token:
        st.error("🔴 Không lấy được Token API Feishu. Hãy kiểm tra lại App ID và App Secret.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
        
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    max_retries = 5  # Đã tăng lên 5 lần thử
    res_data = None
    
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            elif "not ready" in str(res.get("msg")).lower():
                if attempt < max_retries - 1:
                    time.sleep(5)  # Đã tăng thời gian chờ lên 5 giây mỗi lần
                    continue
                else: 
                    st.error("🔴 API Feishu báo 'Not ready' quá lâu.")
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else: 
                st.error(f"🔴 Lỗi từ Feishu API: {res.get('msg')} (Mã lỗi: {res.get('code')})")
                return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception as e: 
            st.error(f"🔴 Lỗi kết nối mạng hoặc timeout: {str(e)}")
            return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    
    if not vals:
        st.error("🔴 File Feishu đang trống rỗng không có dữ liệu!")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
    if len(vals) < 75: 
        st.error(f"🔴 Cấu trúc file bị lỗi! Cần ít nhất 75 dòng để đọc, nhưng hiện tại file chỉ có {len(vals)} dòng.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except: return np.nan

    try:
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

        def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, shc_idx, sht_idx, lhc_idx, lht_idx, cot_total_idx, cot_ontime_idx):
            data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days)]}
            data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
            data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
            data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
            data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
            data["Total Process Vol"] = [clean_val(tproc_vol_idx, c) for c in cols_to_scan]
            data["Total Process Wgt"] = [clean_val(tproc_wgt_idx, c) for c in cols_to_scan]
            data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
            data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan] 
            data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
            
            data["COT Total"] = [clean_val(cot_total_idx, c) for c in cols_to_scan]
            data["COT Ontime"] = [clean_val(cot_ontime_idx, c) for c in cols_to_scan]
            data["COT Rate (%)"] = [(o / t * 100) if (t > 0) else np.nan for t, o in zip(data["COT Total"], data["COT Ontime"])]

            data["Shuttle Chuyến"] = [clean_val(shc_idx, c) for c in cols_to_scan]
            data["Linehaul Chuyến"] = [clean_val(lhc_idx, c) for c in cols_to_scan]
            data["Shuttle Late"] = [clean_val(sht_idx, c) for c in cols_to_scan]
            data["Linehaul Late"] = [clean_val(lht_idx, c) for c in cols_to_scan]

            sh_c_list = data["Shuttle Chuyến"]
            sh_t_list = data["Shuttle Late"]
            lh_c_list = data["Linehaul Chuyến"]
            lh_t_list = data["Linehaul Late"]

            data["LH Rate (%)"] = [(c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan for c, t in zip(lh_c_list, lh_t_list)]
            data["SH Rate (%)"] = [(c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan for c, t in zip(sh_c_list, sh_t_list)]

            valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
            cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
            pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1

            def get_rate(num_idx, den_idx, col_idx):
                if col_idx == -1: return 0
                n = clean_val(num_idx, col_idx)
                d = clean_val(den_idx, col_idx)
                return (n / d * 100) if (d and d > 0) else 0

            weekly_summary = {
                "cw_vin": clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0, "pw_vin": clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_vout": clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0, "pw_vout": clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_tproc_wgt": clean_val(tproc_wgt_idx, cw_idx) if cw_idx != -1 else 0, "pw_tproc_wgt": clean_val(tproc_wgt_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_ms": clean_val(ms_idx, cw_idx) if cw_idx != -1 else 0, "pw_ms": clean_val(ms_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_bl": clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0, "pw_bl": clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
                "cw_cot_ontime": clean_val(cot_ontime_idx, cw_idx) if cw_idx != -1 else 0, "pw_cot_ontime": clean_val(cot_ontime_idx, pw_idx) if pw_idx != -1 else 0,
                
                "cw_lhot": ((clean_val(lhc_idx, cw_idx) - clean_val(lht_idx, cw_idx)) / clean_val(lhc_idx, cw_idx) * 100) if cw_idx != -1 and clean_val(lhc_idx, cw_idx) > 0 else 0,
                "pw_lhot": ((clean_val(lhc_idx, pw_idx) - clean_val(lht_idx, pw_idx)) / clean_val(lhc_idx, pw_idx) * 100) if pw_idx != -1 and clean_val(lhc_idx, pw_idx) > 0 else 0,
                "cw_shot": ((clean_val(shc_idx, cw_idx) - clean_val(sht_idx, cw_idx)) / clean_val(shc_idx, cw_idx) * 100) if cw_idx != -1 and clean_val(shc_idx, cw_idx) > 0 else 0,
                "pw_shot": ((clean_val(shc_idx, pw_idx) - clean_val(sht_idx, pw_idx)) / clean_val(shc_idx, pw_idx) * 100) if pw_idx != -1 and clean_val(shc_idx, pw_idx) > 0 else 0,
                
                "cw_cot": get_rate(cot_ontime_idx, cot_total_idx, cw_idx),
                "pw_cot": get_rate(cot_ontime_idx, cot_total_idx, pw_idx),
            }
            return pd.DataFrame(data), weekly_summary

        data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 23, 24, 42, shc_idx=50, sht_idx=52, lhc_idx=51, lht_idx=53, cot_total_idx=47, cot_ontime_idx=48)
        data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 25, 26, 43, shc_idx=59, sht_idx=61, lhc_idx=60, lht_idx=62, cot_total_idx=56, cot_ontime_idx=57)
        data_sh = extract_hub_data(16, 17, 18, 19, 20, 21, 27, 28, 44, shc_idx=68, sht_idx=70, lhc_idx=69, lht_idx=71, cot_total_idx=65, cot_ontime_idx=66)
        
        return data_hcm, data_bn, data_sh
        
    except Exception as e:
        st.error(f"🔴 Lỗi khi xử lý dữ liệu từ file: {str(e)}.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

# 3. GIAO DIỆN CHÍNH
st.markdown("<div class='main-title'>J&T CARGO KPI DASHBOARD</div>", unsafe_allow_html=True)
data_hcm, data_bn, data_sh = get_data()

df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn
df_sh, sum_sh = data_sh

if df_hcm.empty and df_bn.empty and df_sh.empty:
    st.warning("Đang tải dữ liệu hoặc xảy ra lỗi (xem thông báo lỗi màu đỏ ở trên)...")
    st.stop()

def get_last_7_days(df):
    if df.empty: return df
    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    if valid_df.empty: return df.tail(7).reset_index(drop=True)
    last_idx = valid_df.index[-1]
    start_idx = max(0, last_idx - 6)
    return df.iloc[start_idx:last_idx+1].reset_index(drop=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    " HỒ CHÍ MINH ", " BẮC NINH ", " SH DC ",
    " HCM (7 NGÀY)", " BN (7 NGÀY)", " SH DC (7 NGÀY)"
])

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) and pd.isna(prev): return f"<td style='text-align: center;'></td><td class='col-num'></td><td class='col-num'></td>"
    if pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct and pd.notna(cur) else format_vietnam(cur)
        if pd.isna(cur): cur_str = ""
        return f"<td style='text-align: center; font-size: 16px;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
    if pd.isna(cur):
        prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
        return f"<td style='text-align: center; font-size: 16px;'>-</td><td class='col-num'>-</td><td class='col-num'>{prev_str}</td>"

    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    
    if diff > 0: bg_color, text_color, sign = "#dcfce7", "#15803d", "+"
    elif diff < 0: bg_color, text_color, sign = "#fee2e2", "#b91c1c", ""
    else: bg_color, text_color, sign = "transparent", "#1e293b", ""
    if inverse and diff != 0:
        bg_color = "#fee2e2" if diff > 0 else "#dcfce7"
        text_color = "#b91c1c" if diff > 0 else "#15803d"
        
    wow_str = f"{sign}{pct:.1f}%" if not is_pct else f"{sign}{diff:.1f}%"
    return f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: 900; text-align: center; font-size: 17px;'>{wow_str}</td><td class='col-num'>{format_vietnam(cur) if not is_pct else f'{cur:.2f}%'}</td><td class='col-num'>{format_vietnam(prev) if not is_pct else f'{prev:.2f}%'}</td>"

def clean_layout(fig, title):
    fig.update_layout(title=dict(text=title, font=dict(size=26, weight='bold', color='#1e3a8a')), plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=70, b=30, l=10, r=10), xaxis=dict(showgrid=False, tickfont=dict(size=14, color='#1e293b', weight='bold'), tickangle=-45), yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickfont=dict(size=16, color='#1e293b', weight='bold'), zeroline=False), hoverlabel=dict(font_size=18))
    fig.update_traces(cliponaxis=False)
    return fig

def render_dashboard(df, summary, primary_color, period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=False):
    if df.empty: return
    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    actual_cols = min(len(valid_df), num_daily_cols)
    data_slice = valid_df.tail(actual_cols + 1).reset_index(drop=True)
    
    if len(data_slice) > actual_cols: d_names = data_slice['Ngày'].tolist()[1:]
    else: d_names = data_slice['Ngày'].tolist()
        
    pad_len = num_daily_cols - len(d_names)
    d_display = ["-"] * pad_len + d_names

    def get_d(col_name, is_pct=False, inverse=False):
        vals = data_slice[col_name].tolist()
        if len(vals) > actual_cols:
            cur_vals = vals[1:]
            prev_vals = vals[:-1]
        else:
            cur_vals = vals
            prev_vals = [np.nan] + vals[:-1]
            
        cur_vals = [np.nan] * pad_len + cur_vals
        prev_vals = [np.nan] * pad_len + prev_vals
        
        display_strs = []
        base_style = "font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 17px; font-weight: 700;"
        
        for i in range(num_daily_cols):
            cur = cur_vals[i]
            prev = prev_vals[i]
            
            if pd.isna(cur) or str(cur).strip() == "":
                display_strs.append("<td class='col-num'></td>")
                continue
                
            cur_str = f"{cur:.1f}%" if is_pct else format_vietnam(cur)
            
            if pd.notna(prev) and str(prev).strip() != "":
                diff = cur - prev
                if diff < 0: 
                    color = "#15803d" if inverse else "#dc2626" 
                    icon = "↓"
                    cur_str = f"<span style='color: {color}; {base_style}'>{cur_str} <span style='font-size:14px; font-weight:900;'>{icon}</span></span>"
                elif diff > 0: 
                    color = "#dc2626" if inverse else "#15803d" 
                    icon = "↑"
                    cur_str = f"<span style='color: {color}; {base_style}'>{cur_str} <span style='font-size:14px; font-weight:900;'>{icon}</span></span>"
                else:
                    cur_str = f"<span style='color: #475569; {base_style}'>{cur_str}</span>"
            else:
                cur_str = f"<span style='color: #1e293b; {base_style}'>{cur_str}</span>"
            
            # Tô màu nền xen kẽ để dễ nhìn (trắng/xám nhạt)
            bg_color = "#f8fafc" if i % 2 == 0 else "#ffffff"
            display_strs.append(f"<td class='col-num' style='background-color: {bg_color};'>{cur_str}</td>")
            
        return "".join(display_strs)

    t_vin = df['Inbound Vol'].sum(skipna=True) 
    t_vout = df['Outbound Vol'].sum(skipna=True) 
    t_tproc_vol = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt = df['Total Process Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    cot_ontime_mtd = df['COT Ontime'].sum(skipna=True)
    
    lh_total_chuyen = df['Linehaul Chuyến'].fillna(0).sum()
    lh_total_tre = df['Linehaul Late'].fillna(0).sum()
    lhot_mtd = ((lh_total_chuyen - lh_total_tre) / lh_total_chuyen * 100) if lh_total_chuyen > 0 else 0
    sh_total_chuyen = df['Shuttle Chuyến'].fillna(0).sum()
    sh_total_tre = df['Shuttle Late'].fillna(0).sum()
    shot_mtd = ((sh_total_chuyen - sh_total_tre) / sh_total_chuyen * 100) if sh_total_chuyen > 0 else 0
    cot_mtd = (df['COT Ontime'].sum() / df['COT Total'].sum() * 100) if df['COT Total'].sum() > 0 else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(f"Inbound | 入库 ({period_label})", format_vietnam(t_vin))
    c2.metric(f"Outbound | 出库 ({period_label})", format_vietnam(t_vout))
    c3.metric(f"Tổng lượng hàng xử lý | 总处理量 ({period_label})", format_vietnam(t_tproc_vol))
    c4.metric(f"Trọng lượng | 重量 (Kg)", format_vietnam(t_tproc_wgt))
    c5.metric(f"Missort | 错分 ({period_label})", format_vietnam(t_ms))
    c6.metric(f"Backlog | 积压 ({period_label})", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)

    header_wow = """<th style="width: 100px;">WOW | 环比</th><th>Tuần này | 本周</th><th>Tuần trước | 上周</th>""" if show_weekly else ""
    daily_headers = "".join([f"<th style='background-color: #1e40af;'>{d}</th>" for d in d_display])

    def build_row(kpi_title, rowspan, kpi_color, metric_name, wow_cur, wow_prev, mtd_val, col_name, is_pct=False, inverse=False, is_first=False):
        kpi_td = f'<td rowspan="{rowspan}" class="col-pillar" style="color:{kpi_color};">{kpi_title}</td>' if is_first else ''
        wow_td = get_wow_cell(wow_cur, wow_prev, is_pct, inverse) if show_weekly else ''
        mtd_str = f"{mtd_val:.1f}%" if is_pct else format_vietnam(mtd_val)
        d_tds = get_d(col_name, is_pct, inverse)
        return f"<tr>{kpi_td}<td class='col-metric'>{metric_name}</td>{wow_td}<td class='col-mtd'>{mtd_str}</td>{d_tds}</tr>"

    row1 = build_row("Sản Lượng | 生产", 3, "#0284c7", "Inbound (đơn) | 入库单量", summary['cw_vin'], summary['pw_vin'], t_vin, 'Inbound Vol', is_first=True)
    row2 = build_row("", 3, "", "Outbound (đơn) | 出库单量", summary['cw_vout'], summary['pw_vout'], t_vout, 'Outbound Vol')
    row3 = build_row("", 3, "", "Trọng lượng (kg) | 重量 kg", summary['cw_tproc_wgt'], summary['pw_tproc_wgt'], t_tproc_wgt, 'Total Process Wgt')
    row4 = build_row("Chất Lượng | 质量", 4, "#dc2626", "Missort (đơn) | 错分单量", summary['cw_ms'], summary['pw_ms'], t_ms, 'Missort', inverse=True, is_first=True)
    row5 = build_row("", 4, "", "Backlog (đơn) | 积压单量", summary['cw_bl'], summary['pw_bl'], t_bl, 'Backlog', inverse=True)
    row6 = build_row("", 4, "", "Tổng đơn gửi đúng COT | 按COT准时出库的订单总量", summary['cw_cot_ontime'], summary['pw_cot_ontime'], cot_ontime_mtd, 'COT Ontime')
    row7 = build_row("", 4, "", "% Sent Volume Ontime | 准时出库 %", summary['cw_cot'], summary['pw_cot'], cot_mtd, 'COT Rate (%)', is_pct=True)
    row8 = build_row("Vận Tải | 运输", 2, "#059669", "Tỷ lệ xe linehaul đúng cot (%) | 干线准时COT比例", summary['cw_lhot'], summary['pw_lhot'], lhot_mtd, 'LH Rate (%)', is_pct=True, is_first=True)
    row9 = build_row("", 2, "", "Tỷ lệ xe Shuttle đúng cot (%) | 摆渡准时COT率", summary['cw_shot'], summary['pw_shot'], shot_mtd, 'SH Rate (%)', is_pct=True)

    st.markdown(f"""
    <div style="overflow-x: auto;">
        <table class="kpi-table" style="min-width: 1000px;">
            <thead><tr><th>KPI</th><th style="width: 20%;">Hạng mục | 指标名称</th>{header_wow}<th>{period_label} | 累计</th>{daily_headers}</tr></thead>
            <tbody>{row1}{row2}{row3}{row4}{row5}{row6}{row7}{row8}{row9}</tbody>
        </table>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"<h3 style='color: {primary_color}; font-weight: 900; font-size: 28px; margin-top: 30px; border-bottom: 3px solid {primary_color}; padding-bottom: 5px;'>1. Sản Lượng & Năng Suất | 生产与产能</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    
    with col1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound | 入库", fill='tozeroy', mode='lines+text', text=[f"<b>{format_vietnam(v)}</b>" if v > 0 else "" for v in df['Inbound Vol']], textposition="top center", textfont=dict(size=16, color='#0284c7', family="Arial Black"), line=dict(color='#0284c7', width=4)))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound | 出库", line=dict(color='#f59e0b', dash='dot', width=4)))
        fig_vol = clean_layout(fig_vol, "Inbound & Outbound hàng ngày | 每日入库/出库")
        fig_vol.update_layout(legend=dict(orientation="h", y=1.1, font=dict(size=16)), height=500, uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_vol, use_container_width=True)
        
    with col2:
        fig_prod_v = go.Figure()
        fig_prod_v.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], name="Năng suất", marker_color='#38bdf8', opacity=0.9, text=[f"<b>{format_vietnam(v)}</b>" if v > 0 else "" for v in df['Total Process Vol']], textposition='inside', textangle=-90, insidetextanchor='end', textfont=dict(size=16, color='#0f172a') ))
        fig_prod_v.add_trace(go.Scatter(x=df['Ngày'], y=df['Total Process Vol'], name="Xu hướng", line=dict(color='#dc2626', width=4, shape='spline')))
        fig_prod_v = clean_layout(fig_prod_v, "Năng suất | 产能 (Số đơn | 单数)")
        fig_prod_v.update_layout(height=500, showlegend=False, uniformtext=dict(minsize=14, mode='show')) 
        st.plotly_chart(fig_prod_v, use_container_width=True)
        
    with col3:
        fig_prod_w = go.Figure()
        fig_prod_w.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], name="Trọng lượng", marker_color='#818cf8', opacity=0.9, text=[f"<b>{format_vietnam(v)}</b>" if v > 0 else "" for v in df['Total Process Wgt']], textposition='inside', textangle=-90, insidetextanchor='end', textfont=dict(size=16, color='#ffffff') ))
        fig_prod_w.add_trace(go.Scatter(x=df['Ngày'], y=df['Total Process Wgt'], name="Xu hướng", line=dict(color='#dc2626', width=4, shape='spline')))
        fig_prod_w = clean_layout(fig_prod_w, "Năng suất | 产能 (Trọng lượng | 重量 kg)")
        fig_prod_w.update_layout(height=500, showlegend=False, uniformtext=dict(minsize=14, mode='show')) 
        st.plotly_chart(fig_prod_w, use_container_width=True)

    st.markdown(f"<h3 style='color: {primary_color}; font-weight: 900; font-size: 28px; margin-top: 40px; border-bottom: 3px solid {primary_color}; padding-bottom: 5px;'>2. Quản lý Vận Tải & COT | 运输与准时出库管理</h3>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2) 
    with col_t1:
        fig_trans = go.Figure()
        fig_trans.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Chuyến'], name="Shuttle", marker_color='#3b82f6', text=[int(x) if x>0 else "" for x in df['Shuttle Chuyến']], textposition='inside', textfont=dict(size=16, color='white', weight='bold')))
        fig_trans.add_trace(go.Bar(x=df['Ngày'], y=df['Linehaul Chuyến'], name="Linehaul", marker_color='#f97316', text=[int(x) if x>0 else "" for x in df['Linehaul Chuyến']], textposition='inside', textfont=dict(size=16, color='white', weight='bold')))
        fig_trans = clean_layout(fig_trans, "Tổng số chuyến xe (Shuttle & Linehaul) | 总车次")
        fig_trans.update_layout(barmode='stack', height=500, legend=dict(orientation="h", y=-0.2, font=dict(size=16)), uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_trans, use_container_width=True)

    with col_t2:
        fig_cot = go.Figure()
        fig_cot.add_trace(go.Bar(x=df['Ngày'], y=df['COT Total'], name="Tổng đơn", marker_color='#bae6fd', opacity=0.8, text=[format_vietnam(x) if pd.notna(x) and x > 0 else "" for x in df['COT Ontime']], textposition='inside', textangle=-90, insidetextanchor='end', textfont=dict(size=16, color='#0f172a'), insidetextfont=dict(size=16, color='#0f172a')))
        fig_cot.add_trace(go.Scatter(x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ", yaxis="y2", line=dict(color='#059669', width=5, shape='spline'), mode='lines+markers+text', text=[f"{v:.0f}%" if v > 0 else "" for v in df['COT Rate (%)']], textposition="top center", textfont=dict(size=18, color='#064e3b', weight='bold')))
        fig_cot = clean_layout(fig_cot, "% Sent Volume Ontime | 准时出库率 %")
        fig_cot.update_layout(height=500, showlegend=False, yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False, tickfont=dict(size=16, color='#1e293b', weight='bold')), uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_cot, use_container_width=True)

    col_l1, col_l2, col_l3 = st.columns([1, 1, 1.2])
    with col_l1:
        fig_sh_late = go.Figure()
        fig_sh_late.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Late'], marker_color='#ef4444', text=[int(x) if x>0 else "" for x in df['Shuttle Late']], textposition='outside', textfont=dict(size=16, color='#991b1b', weight='bold')))
        fig_sh_late = clean_layout(fig_sh_late, "Shuttle Late | 支线延迟")
        fig_sh_late.update_layout(height=400, uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_sh_late, use_container_width=True)
    with col_l2:
        fig_lh_late = go.Figure()
        fig_lh_late.add_trace(go.Bar(x=df['Ngày'], y=df['Linehaul Late'], marker_color='#f43f5e', text=[int(x) if x>0 else "" for x in df['Linehaul Late']], textposition='outside', textfont=dict(size=16, color='#9f1239', weight='bold')))
        fig_lh_late = clean_layout(fig_lh_late, "Linehaul Late | 干线延迟")
        fig_lh_late.update_layout(height=400, uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_lh_late, use_container_width=True)
    with col_l3:
        fig_bl = go.Figure()
        fig_bl.add_trace(go.Bar(x=df['Ngày'], y=df['Backlog'], marker_color='#f59e0b', text=[format_vietnam(x) if x>0 else "" for x in df['Backlog']], textposition='outside', textfont=dict(size=16, color='#b45309', weight='bold')))
        fig_bl = clean_layout(fig_bl, "Backlog | 积压")
        fig_bl.update_layout(height=400, uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_bl, use_container_width=True)
        
    # HIỂN THỊ RAW DATA THEO CỜ LỆNH
    if show_raw_data:
        with st.expander("🔍 Chi tiết dữ liệu thô | 详细数据"):
            raw = df.copy()
            for c in raw.columns:
                if c != "Ngày":
                    def safe_format(x, is_pct):
                        if pd.isna(x) or str(x).strip() == "": return ""
                        try:
                            return f"{float(x):.1f}%" if is_pct else format_vietnam(float(x))
                        except: return str(x)
                    raw[c] = raw[c].apply(lambda x: safe_format(x, "%" in c))
            st.dataframe(raw.set_index("Ngày").T, use_container_width=True)

# --- 3 TABS GỐC (HIỂN THỊ MTD - 3 NGÀY + BẬT DATA THÔ) ---
with tab1:
    render_dashboard(df_hcm, sum_hcm, "#0284c7", period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=True)
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669", period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=True) 
with tab3:
    render_dashboard(df_sh, sum_sh, "#8b5cf6", period_label="MTD", show_weekly=True, num_daily_cols=3, show_raw_data=True) 

# --- 3 TABS MỚI (HIỂN THỊ 7 NGÀY - TẮT DATA THÔ) ---
with tab4:
    render_dashboard(get_last_7_days(df_hcm), sum_hcm, "#0284c7", period_label="7 Ngày", show_weekly=False, num_daily_cols=7, show_raw_data=False)
with tab5:
    render_dashboard(get_last_7_days(df_bn), sum_bn, "#059669", period_label="7 Ngày", show_weekly=False, num_daily_cols=7, show_raw_data=False)
with tab6:
    render_dashboard(get_last_7_days(df_sh), sum_sh, "#8b5cf6", period_label="7 Ngày", show_weekly=False, num_daily_cols=7, show_raw_data=False)
