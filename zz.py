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
    .kpi-table th { background-color: #1e3a8a; color: #ffffff; padding: 14px 10px; text-align: center; border: 1px solid #94a3b8; font-size: 16px; font-weight: 800; }
    .kpi-table td { padding: 12px 10px; border: 1px solid #cbd5e1; font-size: 16px; vertical-align: middle; color: #1e293b; }
    .col-pillar { font-weight: 800; text-align: center; background-color: #f1f5f9; font-size: 17px; }
    .col-metric { font-weight: 700; color: #0f172a; }
    .col-num { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 17px; font-weight: 700; color: #0f172a;}
    .col-mtd { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 19px; font-weight: 900; background-color: #dcfce7; color: #166534; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08); transition: transform 0.2s ease-in-out; border-left: 5px solid #2563eb; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.15); }
    div[data-testid="metric-container"] label { font-size: 17px !important; font-weight: 700 !important; color: #334155 !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 36px !important; font-weight: 900 !important; color: #1e3a8a !important; }
    .main-title { text-align: center; font-weight: 900; color: #0f172a; font-size: 46px; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
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
                else: 
                    st.error("🔴 API Feishu báo 'Not ready' quá lâu.")
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else: 
                st.error(f"🔴 Lỗi từ Feishu API: {res.get('msg')} (Mã lỗi: {res.get('code')})")
                return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception as e: 
            st.error(f"🔴 Lỗi kết nối mạng hoặc timeout: {str(e)}")
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    
    if not vals:
        st.error("🔴 File Feishu đang trống rỗng không có dữ liệu!")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})
    if len(vals) < 55: 
        st.error(f"🔴 Cấu trúc file bị lỗi! Cần ít nhất 55 dòng để đọc, nhưng hiện tại file chỉ có {len(vals)} dòng. Có ai đó đã lỡ xóa dòng rồi!")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

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

            sh_c_list, sh_t_list = data["Shuttle Chuyến"], data["Shuttle Late"]
            lh_c_list, lh_t_list = data["Linehaul Chuyến"], data["Linehaul Late"]

            data["LH Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(lh_c_list, lh_t_list)]
            data["LH Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(lh_c_list, lh_t_list)]
            data["Shuttle Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(sh_c_list, sh_t_list)]
            data["Shuttle Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(sh_c_list, sh_t_list)]
            
            # Tính % Tỷ lệ xe đúng giờ cho 3 ngày gần nhất
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

        data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, shc_idx=38, sht_idx=40, lhc_idx=39, lht_idx=41, cot_total_idx=35, cot_ontime_idx=36)
        data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, shc_idx=47, sht_idx=49, lhc_idx=48, lht_idx=50, cot_total_idx=44, cot_ontime_idx=45)
        return data_hcm, data_bn
        
    except Exception as e:
        st.error(f"🔴 Lỗi khi xử lý dữ liệu từ file: {str(e)}. Cấu trúc file có thể đã bị thay đổi (xóa dòng/cột)!")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

# 3. GIAO DIỆN CHÍNH
st.markdown("<div class='main-title'>J&T CARGO KPI DASHBOARD</div>", unsafe_allow_html=True)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu hoặc xảy ra lỗi (xem thông báo lỗi màu đỏ ở trên)...")
    st.stop()

tab1, tab2 = st.tabs(["📌 HỒ CHÍ MINH HUB", "📌 BẮC NINH HUB"])

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

# ĐÃ FIX: CHỐNG LỖI "nan%" VÀ TRẢ VỀ Ô TRỐNG SẠCH ĐẸP NẾU KHÔNG CÓ DỮ LIỆU
def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) and pd.isna(prev):
        return f"<td style='text-align: center;'></td><td class='col-num'></td><td class='col-num'></td>"
        
    if pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct and pd.notna(cur) else format_vietnam(cur)
        if pd.isna(cur): cur_str = ""
        return f"<td style='text-align: center; font-size: 16px;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
        
    if pd.isna(cur):
        prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
        return f"<td style='text-align: center; font-size: 16px;'>-</td><td class='col-num'>-</td><td class='col-num'>{prev_str}</td>"

    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    
    if diff > 0:
        bg_color, text_color, sign = "#dcfce7", "#15803d", "+"
        if inverse: bg_color, text_color = "#fee2e2", "#b91c1c"
    elif diff < 0:
        bg_color, text_color, sign = "#fee2e2", "#b91c1c", ""
        if inverse: bg_color, text_color = "#dcfce7", "#15803d"
    else: bg_color, text_color, sign = "transparent", "#1e293b", ""
    
    wow_str = f"{sign}{pct:.1f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    return f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: 900; text-align: center; font-size: 17px;'>{wow_str}</td><td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"

def clean_layout(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=26, weight='bold', color='#1e3a8a')),
        plot_bgcolor='white', paper_bgcolor='white', margin=dict(t=70, b=30, l=10, r=10),
        xaxis=dict(
            showgrid=False, 
            tickfont=dict(size=14, color='#1e293b', weight='bold'),
            tickmode='linear', 
            tickangle=-45 
        ),
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', tickfont=dict(size=16, color='#1e293b', weight='bold'), zeroline=False),
        hoverlabel=dict(font_size=18)
    )
    fig.update_traces(cliponaxis=False)
    return fig

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # Lấy 3 ngày có dữ liệu gần nhất
    valid_df = df.dropna(subset=['Inbound Vol'])
    valid_df = valid_df[valid_df['Inbound Vol'] > 0]
    last_3 = valid_df.tail(3)
    pad_len = 3 - len(last_3)
    d_names = ["-"] * pad_len + last_3['Ngày'].tolist()

    # Hàm tạo ô hiển thị dữ liệu 3 ngày đó
    def get_d(col_name, is_pct=False):
        vals = []
        for i in range(pad_len): vals.append("")
        for v in last_3[col_name]:
            if pd.isna(v) or str(v).strip() == "": vals.append("")
            else: vals.append(f"{v:.1f}%" if is_pct else format_vietnam(v))
        # Màu nền đậm dần cho 3 ngày
        return f"<td class='col-num' style='background-color: #f8fafc;'>{vals[0]}</td><td class='col-num' style='background-color: #f1f5f9;'>{vals[1]}</td><td class='col-num' style='background-color: #e2e8f0; font-weight: 800; color: #1e3a8a;'>{vals[2]}</td>"

    # Tính MTD
    t_vin = df['Inbound Vol'].sum(skipna=True) 
    t_vout = df['Outbound Vol'].sum(skipna=True) 
    t_tproc_vol = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt = df['Total Process Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    cot_ontime_mtd = df['COT Ontime'].sum(skipna=True)
    
    lh_total = df['LH Đúng Giờ'].fillna(0).sum() + df['LH Trễ'].fillna(0).sum()
    sh_total = df['Shuttle Đúng Giờ'].fillna(0).sum() + df['Shuttle Trễ'].fillna(0).sum()
    lhot_mtd = (df['LH Đúng Giờ'].fillna(0).sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df['Shuttle Đúng Giờ'].fillna(0).sum() / sh_total * 100) if sh_total > 0 else 0
    cot_mtd = (df['COT Ontime'].sum() / df['COT Total'].sum() * 100) if df['COT Total'].sum() > 0 else 0

    # 1. METRICS 
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound | 入库 (MTD)", format_vietnam(t_vin))
    c2.metric("Outbound | 出库 (MTD)", format_vietnam(t_vout))
    c3.metric("Tổng lượng hàng xử lý | 总处理量 (MTD)", format_vietnam(t_tproc_vol))
    c4.metric("Trọng lượng | 重量 (Kg)", format_vietnam(t_tproc_wgt))
    c5.metric("Missort | 错分 (MTD)", format_vietnam(t_ms))
    c6.metric("Backlog | 积压 (MTD)", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. WOW TABLE (ĐÃ ÉP CỘT HẠNG MỤC XUỐNG 20% VÀ THÊM 3 CỘT NGÀY CUỐI)
    st.markdown(f"""<table class="kpi-table">
        <thead>
            <tr>
                <th>KPI</th>
                <th style="width: 20%;">Hạng mục | 指标名称</th>
                <th style="width: 100px;">WOW | 环比</th>
                <th>Tuần này | 本周</th>
                <th>Tuần trước | 上周</th>
                <th>MTD | 累计</th>
                <th style="background-color: #3b82f6;">{d_names[0]}</th>
                <th style="background-color: #2563eb;">{d_names[1]}</th>
                <th style="background-color: #1d4ed8;">{d_names[2]}</th>
            </tr>
        </thead>
        <tbody>
            <tr><td rowspan="3" class="col-pillar" style="color:#0284c7;">Sản Lượng | 生产</td><td class="col-metric">Inbound (đơn) | 入库单量</td>{get_wow_cell(summary['cw_vin'], summary['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td>{get_d('Inbound Vol')}</tr>
            <tr><td class="col-metric">Outbound (đơn) | 出库单量</td>{get_wow_cell(summary['cw_vout'], summary['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td>{get_d('Outbound Vol')}</tr>
            <tr><td class="col-metric">Trọng lượng (kg) | 重量 kg</td>{get_wow_cell(summary['cw_tproc_wgt'], summary['pw_tproc_wgt'])}<td class="col-mtd">{format_vietnam(t_tproc_wgt)}</td>{get_d('Total Process Wgt')}</tr>
            <tr><td rowspan="4" class="col-pillar" style="color:#dc2626;">Chất Lượng | 质量</td><td class="col-metric">Missort (đơn) | 错分单量</td>{get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td>{get_d('Missort')}</tr>
            <tr><td class="col-metric">Backlog (đơn) | 积压单量</td>{get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td>{get_d('Backlog')}</tr>
            <tr><td class="col-metric">Tổng đơn gửi đúng COT | 按COT准时出库的订单总量</td>{get_wow_cell(summary['cw_cot_ontime'], summary['pw_cot_ontime'])}<td class="col-mtd">{format_vietnam(cot_ontime_mtd)}</td>{get_d('COT Ontime')}</tr>
            <tr><td class="col-metric">% Sent Volume Ontime | 准时出库 %</td>{get_wow_cell(summary['cw_cot'], summary['pw_cot'], is_pct=True)}<td class="col-mtd">{cot_mtd:.1f}%</td>{get_d('COT Rate (%)', is_pct=True)}</tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#059669;">Vận Tải | 运输</td><td class="col-metric"> Tỷ lệ xe linehual sai cot (%) | 干线错COT比例</td>{get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td>{get_d('LH Rate (%)', is_pct=True)}</tr>
            <tr><td class="col-metric">Tỷ lệ xe Shuttle sai cot (%) | 摆渡错COT率</td>{get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td>{get_d('SH Rate (%)', is_pct=True)}</tr>
        </tbody></table>""", unsafe_allow_html=True)

    # 3. BIỂU ĐỒ SẢN LƯỢNG & NĂNG SUẤT
    st.markdown(f"<h3 style='color: {primary_color}; font-weight: 900; font-size: 28px; margin-top: 30px; border-bottom: 3px solid {primary_color}; padding-bottom: 5px;'>1. Sản Lượng & Năng Suất | 生产与产能</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    
    with col1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound | 入库", fill='tozeroy', mode='lines+text', 
                                     text=[f"<b>{format_vietnam(v)}</b>" if v > 0 else "" for v in df['Inbound Vol']], 
                                     textposition="top center", textfont=dict(size=16, color='#0284c7', family="Arial Black"), line=dict(color='#0284c7', width=4)))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound | 出库", line=dict(color='#f59e0b', dash='dot', width=4)))
        fig_vol = clean_layout(fig_vol, "Inbound & Outbound hàng ngày | 每日入库/出库")
        fig_vol.update_layout(legend=dict(orientation="h", y=1.1, font=dict(size=16)), height=500, uniformtext=dict(minsize=14, mode='show'))
        st.plotly_chart(fig_vol, use_container_width=True)
        
    with col2:
        fig_prod_v = go.Figure()
        fig_prod_v.add_trace(go.Bar(
            x=df['Ngày'], 
            y=df['Total Process Vol'], 
            name="Năng suất", 
            marker_color='#38bdf8', 
            opacity=0.9,
            text=[f"<b>{format_vietnam(v)}</b>" if v > 0 else "" for v in df['Total Process Vol']], 
            textposition='inside', 
            textangle=-90, 
            insidetextanchor='end', 
            textfont=dict(size=16, color='#0f172a') 
        ))
        fig_prod_v.add_trace(go.Scatter(x=df['Ngày'], y=df['Total Process Vol'], name="Xu hướng", line=dict(color='#dc2626', width=4, shape='spline')))
        fig_prod_v = clean_layout(fig_prod_v, "Năng suất | 产能 (Số đơn | 单数)")
        fig_prod_v.update_layout(height=500, showlegend=False, uniformtext=dict(minsize=14, mode='show')) 
        st.plotly_chart(fig_prod_v, use_container_width=True)
        
    with col3:
        fig_prod_w = go.Figure()
        fig_prod_w.add_trace(go.Bar(
            x=df['Ngày'], 
            y=df['Total Process Wgt'], 
            name="Trọng lượng", 
            marker_color='#818cf8', 
            opacity=0.9,
            text=[f"<b>{format_vietnam(v)}</b>" if v > 0 else "" for v in df['Total Process Wgt']], 
            textposition='inside', 
            textangle=-90, 
            insidetextanchor='end', 
            textfont=dict(size=16, color='#ffffff') 
        ))
        fig_prod_w.add_trace(go.Scatter(x=df['Ngày'], y=df['Total Process Wgt'], name="Xu hướng", line=dict(color='#dc2626', width=4, shape='spline')))
        fig_prod_w = clean_layout(fig_prod_w, "Năng suất | 产能 (Trọng lượng | 重量 kg)")
        fig_prod_w.update_layout(height=500, showlegend=False, uniformtext=dict(minsize=14, mode='show')) 
        st.plotly_chart(fig_prod_w, use_container_width=True)

    # 4. BIỂU ĐỒ VẬN TẢI & COT (%)
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
        fig_cot.add_trace(go.Bar(
            x=df['Ngày'], 
            y=df['COT Total'], 
            name="Tổng đơn", 
            marker_color='#bae6fd', 
            opacity=0.8,
            text=[format_vietnam(x) if pd.notna(x) and x > 0 else "" for x in df['COT Ontime']],
            textposition='inside',
            textangle=-90, 
            insidetextanchor='end',
            textfont=dict(size=16, color='#0f172a'),
            insidetextfont=dict(size=16, color='#0f172a')
        ))
        
        fig_cot.add_trace(go.Scatter(
            x=df['Ngày'], y=df['COT Rate (%)'], name="Tỷ lệ", yaxis="y2", 
            line=dict(color='#059669', width=5, shape='spline'), mode='lines+markers+text',
            text=[f"{v:.0f}%" if v > 0 else "" for v in df['COT Rate (%)']], 
            textposition="top center", 
            textfont=dict(size=18, color='#064e3b', weight='bold')
        ))
        
        fig_cot = clean_layout(fig_cot, "% Sent Volume Ontime | 准时出库率 %")
        fig_cot.update_layout(
            height=500, 
            showlegend=False, 
            yaxis2=dict(overlaying='y', side='right', range=[0, 110], showgrid=False, tickfont=dict(size=16, color='#1e293b', weight='bold')),
            uniformtext=dict(minsize=14, mode='show') 
        )
        st.plotly_chart(fig_cot, use_container_width=True)

    # Dòng 2: TRỄ XE & BACKLOG
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

    # 5. CHI TIẾT DỮ LIỆU THÔ
    with st.expander("🔍 Chi tiết dữ liệu thô | 详细数据"):
        df_display = df.copy()
        for col in df_display.columns:
            if col == "Ngày": continue
            def clean_format(x, is_pct):
                if pd.isna(x) or str(x).strip().lower() in ["none", "nan", ""]: return ""
                try:
                    f_x = float(x)
                    if f_x == 0: return ""
                    return format_vietnam(f_x) if not is_pct else f"{f_x:.1f}%"
                except: return str(x)
            df_display[col] = df_display[col].apply(lambda x: clean_format(x, "%" in col))
        st.dataframe(df_display.set_index("Ngày").T, use_container_width=True)

with tab1:
    render_dashboard(df_hcm, sum_hcm, "#0284c7") 
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669")
