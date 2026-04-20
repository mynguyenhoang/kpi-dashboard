import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time

# 1. CẤU HÌNH TRANG & CSS (Giữ nguyên)
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
        # BẠN CẦN THAY APP_ID VÀ APP_SECRET CỦA BẠN VÀO ĐÂY ĐỂ CHẠY THỰC TẾ
        payload = {
            "app_id": "cli_xxxxxxxxxxxxx", 
            "app_secret": "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
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
        
    # Vùng dữ liệu cần bao phủ toàn bộ bảng, bao gồm cả cột Tuần và MTD
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AP80?valueRenderOption=FormattedValue"
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
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else:
                return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception as e:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})
            
    if not res_data:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

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

    # === [BƯỚC 1: FIX LOGIC] Xác định vị trí các cột Tuần và MTD ===
    # Dựa trên ảnh: Cột W15 là cột 3 (chỉ số 2), MTD Monthly Total là cột 7 (chỉ số 6)
    # Ta lấy trực tiếp từ bảng chứ không tự cộng
    weekly_cols = [2, 3, 4, 5]  # Các ô "W15-2026" đến "W18-2026"
    mtd_final_col = 6          # Ô "Monthly Total"

    # Xác định cột bắt đầu dữ liệu thô (Ngày 1)
    # Dựa trên code của bạn, bắt đầu từ cột index 6
    start_col_idx = 7 # Ô "Ngày 1" nằm ở cột H (chỉ số 7)
    
    # Số ngày quét tối đa (trong ảnh là 30 ngày)
    num_days_to_scan = 30 
    cols_to_scan = [start_col_idx + i for i in range(num_days_to_scan)]

    # [BƯỚC 2: FIX LOGIC] Thêm tham số mtd_row_idx để lấy đúng ô MTD từ Feishu
    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx, mtd_row_idxs):
        # 1. Lấy dữ liệu thô hàng ngày cho biểu đồ
        data = {"Ngày": [f"Ngày {i+1}" for i in range(num_days_to_scan)]}
        data["Inbound Vol"] = [clean_val(vin_idx, c) for c in cols_to_scan]
        data["Outbound Vol"] = [clean_val(vout_idx, c) for c in cols_to_scan]
        data["Inbound Wgt"] = [clean_val(win_idx, c) for c in cols_to_scan]
        data["Outbound Wgt"] = [clean_val(wout_idx, c) for c in cols_to_scan]
        data["Missort"] = [clean_val(ms_idx, c) for c in cols_to_scan]
        data["Tỷ lệ Missort (%)"] = [clean_val(ms_rt_idx, c) for c in cols_to_scan] 
        data["Backlog"] = [clean_val(bl_idx, c) for c in cols_to_scan]
        
        # Logistic vận tải cho biểu đồ (cần NaN để ẩn số 0)
        lh_c_list = [clean_val(lhc_idx, c) if pd.notna(clean_val(lhc_idx, c)) else 0 for c in cols_to_scan]
        lh_t_list = [clean_val(lht_idx, c) if pd.notna(clean_val(lht_idx, c)) else 0 for c in cols_to_scan]
        sh_c_list = [clean_val(shc_idx, c) if pd.notna(clean_val(shc_idx, c)) else 0 for c in cols_to_scan]
        sh_t_list = [clean_val(sht_idx, c) if pd.notna(clean_val(sht_idx, c)) else 0 for c in cols_to_scan]

        data["LH Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(lh_c_list, lh_t_list)]
        data["LH Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(lh_c_list, lh_t_list)]
        data["Shuttle Đúng Giờ"] = [(c - t) if (c > 0) else np.nan for c, t in zip(sh_c_list, sh_t_list)]
        data["Shuttle Trễ"] = [t if t > 0 else (np.nan if c == 0 else 0) for c, t in zip(sh_c_list, sh_t_list)]
        
        # 2. Lấy dữ liệu Tổng (MTD) trực tiếp từ ô "Monthly Total"
        # BẠN CẦN ĐIỀN ĐÚNG row_idx CỦA DÒNG 'W15' VÀO ĐÂY TRÊN FEISHU
        cw_idx = weekly_cols[-1] 
        pw_idx = weekly_cols[-2] 
        
        # Logic tính WOW từ 2 tuần gần nhất
        def get_rate_val(c_idx, t_idx, col):
            chuyen = clean_val(c_idx, col)
            tre = clean_val(t_idx, col)
            if chuyen > 0: return ((chuyen - tre) / chuyen * 100)
            return 0

        total_data = {
            # Lấy WOW từ 2 ô Tuần gần nhất
            "cw_vin": clean_val(vin_idx, cw_idx), "pw_vin": clean_val(vin_idx, pw_idx),
            "cw_vout": clean_val(vout_idx, cw_idx), "pw_vout": clean_val(vout_idx, pw_idx),
            "cw_win": clean_val(win_idx, cw_idx), "pw_win": clean_val(win_idx, pw_idx),
            "cw_wout": clean_val(wout_idx, cw_idx), "pw_wout": clean_val(wout_idx, pw_idx),
            "cw_ms": clean_val(ms_idx, cw_idx), "pw_ms": clean_val(ms_idx, pw_idx),
            "cw_bl": clean_val(bl_idx, cw_idx), "pw_bl": clean_val(bl_idx, pw_idx),
            "cw_lhot": get_rate_val(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_rate_val(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_rate_val(shc_idx, sht_idx, cw_idx), "pw_shot": get_rate_val(shc_idx, sht_idx, pw_idx),
            
            # === [FIX LOGIC] Lấy trực tiếp từ ô MTD/Monthly Total trên Feishu ===
            "mtd_vin": clean_val(vin_idx, mtd_final_col),
            "mtd_vout": clean_val(vout_idx, mtd_final_col),
            "mtd_win": clean_val(win_idx, mtd_final_col),
            "mtd_wout": clean_val(wout_idx, mtd_final_col),
            "mtd_ms": clean_val(ms_idx, mtd_final_col),
            # Backlog thường lấy số ngày cuối cùng chứ không sum, hoặc lấy trực tiếp MTD
            "mtd_bl": clean_val(bl_idx, mtd_final_col),
            # Vận tải tỷ lệ MTD cũng cần ô Monthly Total của chuyến chạy và chuyến trễ
            "mtd_lhot": get_rate_val(lhc_idx, lht_idx, mtd_final_col),
            "mtd_shot": get_rate_val(shc_idx, sht_idx, mtd_final_col),
            # Tỷ lệ missort MTD
            "mtd_ms_rate": clean_val(ms_rt_idx, mtd_final_col) 
        }
        
        return pd.DataFrame(data), total_data

    # BẠN CẦN THAY CÁC row_idx CHÍNH XÁC ĐỂ LẤY Ô MTD
    # Ảnh cho thấy các ô Monthly Total nằm ở cột G. Bạn cần xác định dòng MTD là bao nhiêu.
    # Giả sử dòng 'Monthly Total' là 54 và 55 cho HCM và BN. Đổi thành index 53, 54.
    
    # HCM Hub với row_idx dòng MTD là 53
    data_hcm, summary_hcm = extract_hub_data(4, 5, 6, 7, 17, 18, 31, 38, 40, 39, 41, 53)
    # BN Hub với row_idx dòng MTD là 54
    data_bn, summary_bn = extract_hub_data(10, 11, 12, 13, 19, 20, 32, 47, 49, 48, 50, 54)
    
    return (data_hcm, summary_hcm), (data_bn, summary_bn)

# 3. GIAO DIỆN HIỂN THỊ CHUNG
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)

# Lấy dữ liệu với logic mới (trực tiếp lấy MTD từ Feishu)
(df_hcm, sum_hcm), (df_bn, sum_bn) = get_data()

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu hoặc File Feishu trống...")
    st.stop()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

# HÀM ĐỊNH DẠNG SỐ (Giữ nguyên)
def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if prev is None or pd.isna(prev) or prev == 0:
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else (diff / prev * 100)
    # Màu sắc dựa trên logic WOW
    color = "#15803d" if (diff > 0 if not inverse else diff < 0) else "#b91c1c"
    bg = "#dcfce7" if (diff > 0 if not inverse else diff < 0) else "#fee2e2"
    sign = "+" if diff > 0 else ""
    return f"<td style='background-color: {bg}; color: {color}; font-weight: bold; text-align: center;'>{sign}{pct:.0f}%</td><td class='col-num'>{format_vietnam(cur)}</td><td class='col-num'>{format_vietnam(prev)}</td>"

def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # === [FIX LOGIC] Lấy trực tiếp từ summary chứ không tự cộng sum() ===
    t_vin = summary['mtd_vin']
    t_vout = summary['mtd_vout']
    t_ms = summary['mtd_ms']
    t_bl = summary['mtd_bl']
    lhot_mtd = summary['mtd_lhot']
    shot_mtd = summary['mtd_shot']
    # ms_rate_mtd lấy trực tiếp ô tỷ lệ MTD missort trên Feishu
    ms_rate_mtd = summary['mtd_ms_rate'] 
    
    # 1. HEADER METRICS (MTD) - Sử dụng số liệu chính xác từ Feishu
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Inbound (MTD) | 入库总量", format_vietnam(t_vin))
    c2.metric("Tổng Outbound (MTD) | 出库总量", format_vietnam(t_vout))
    c3.metric(f"Tổng Missort (MTD) | 分拣错误 ({ms_rate_mtd:.2f}%)", format_vietnam(t_ms))
    c4.metric("Tổng Backlog (MTD) | 积压货物", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. BẢNG TỔNG HỢP KPI (Giữ nguyên UI)
    html_table = f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>KPI</th><th>Hạng mục</th><th style="width: 100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD (Cả Tháng)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="4" class="col-pillar">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>
                {get_wow_cell(summary['cw_vin'], summary['pw_vin'])}
                <td class="col-mtd">{format_vietnam(t_vin)}</td>
            </tr>
            <tr>
                <td class="col-metric">Inbound (kg)</td>
                {get_wow_cell(summary['cw_win'], summary['pw_win'])}
                <td class="col-mtd">{format_vietnam(summary['mtd_win'])}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (đơn)</td>
                {get_wow_cell(summary['cw_vout'], summary['pw_vout'])}
                <td class="col-mtd">{format_vietnam(t_vout)}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (kg)</td>
                {get_wow_cell(summary['cw_wout'], summary['pw_wout'])}
                <td class="col-mtd">{format_vietnam(summary['mtd_wout'])}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar">Chất Lượng</td><td class="col-metric">Tổng Missort (đơn)</td>
                {get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}
                <td class="col-mtd">{format_vietnam(t_ms)}</td>
            </tr>
            <tr>
                <td class="col-metric">Backlog (đơn)</td>
                {get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}
                <td class="col-mtd">{format_vietnam(t_bl)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar">Vận Tải</td><td class="col-metric">Linehaul (%)</td>
                {get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}
                <td class="col-mtd">{lhot_mtd:.2f}%</td>
            </tr>
            <tr>
                <td class="col-metric">Shuttle (%)</td>
                {get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}
                <td class="col-mtd">{shot_mtd:.2f}%</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(html_table, unsafe_allow_html=True)
    
    # 3. BIỂU ĐỒ - Giữ nguyên vì sử dụng dữ liệu hàng ngày
    # (Biểu đồ vẫn cần sum na để stacked bar không lỗi)
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>1. Biểu Đồ Sản Lượng & Missort</h4>", unsafe_allow_html=True)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Sản lượng Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_vol, use_container_width=True)
    with col_chart2:
        fig_ms = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ms.add_trace(go.Bar(x=df['Ngày'], y=df['Missort'], name="Missort", marker_color='#cbd5e1', opacity=0.8), secondary_y=False)
        fig_ms.add_trace(go.Scatter(x=df['Ngày'], y=df['Tỷ lệ Missort (%)'], name="Tỷ lệ %", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
        fig_ms.update_layout(title_text="Phân tích Missort hàng ngày", plot_bgcolor='white', margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_ms, use_container_width=True)

    # 4. BẢNG DỮ LIỆU THÔ (FIX ẨN SỐ 0)
    # Logic ẩn số 0 nằm ở đây: pandas NaN sẽ được convert thành chuỗi rỗng
    st.markdown(f"<h4 style='color: {primary_color}; font-size: 18px;'>2. Bảng đối soát dữ liệu thô</h4>", unsafe_allow_html=True)
    df_show = df.copy()
    for col in df_show.columns:
        if col != "Ngày":
            if "Tỷ lệ" in col:
                df_show[col] = df_show[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
            else:
                # pandas map với lambda tự định nghĩa để NaN/Empty -> rỗng, số 0 -> "0"
                # format_vietnam trong code của bạn đã trả về rỗng nếu NaN
                df_show[col] = df_show[col].apply(format_vietnam)
    
    # Chuyển Ngày thành Index và Xoay ngang bảng
    df_show = df_show.set_index("Ngày").T
    with st.expander("🔍 Bấm vào đây để xem Bảng Chi Tiết Thô Hàng Ngày", expanded=True):
        st.dataframe(df_show, use_container_width=True)

with tab1:
    render_dashboard(df_hcm, sum_hcm, "#0284c7") 
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669")
