import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# ==========================================
# 1. CẤU HÌNH TRANG & CSS
# ==========================================
st.set_page_config(page_title="J&T Cargo - KPI Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS để điều chỉnh giao diện bảng và các metric
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
    
    /* Style cho Streamlit Metric */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HÀM LẤY DỮ LIỆU TỪ FEISHU
# ==========================================
def get_tenant_access_token():
    """Lấy token để truy cập API Feishu."""
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": "cli_a9456e412bb89bce", 
            "app_secret": "BwSAuHHsv2woEdIGTqJoKboH6i1i7qBB"
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get("tenant_access_token")
    except Exception:
        return None

@st.cache_data(ttl=60) # Cache dữ liệu trong 60 giây
def get_data():
    """Hàm chính để lấy và xử lý dữ liệu từ Feishu Sheet."""
    token = get_tenant_access_token()
    if not token:
        st.error("Không lấy được Token Feishu. Vui lòng kiểm tra lại App ID/Secret.")
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    # URL API Feishu Sheet (v2)
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}

    # Gọi API với cơ chế retry nếu dữ liệu chưa sẵn sàng
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
                    time.sleep(2) # Đợi 2 giây trước khi thử lại
                    continue
                else:
                    return (pd.DataFrame(), {}), (pd.DataFrame(), {})
            else:
                return (pd.DataFrame(), {}), (pd.DataFrame(), {})
        except Exception:
            return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    if not res_data:
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 55: # Đảm bảo đủ số dòng tối thiểu
        return (pd.DataFrame(), {}), (pd.DataFrame(), {})

    # --- HÀM HELPER XỬ LÝ DỮ LIỆU TRONG TRANG NÀY ---
    def clean_val(row_idx, col_idx):
        """Lấy và làm sạch dữ liệu số từ ô tính."""
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                # Bỏ qua ô trống, lỗi formula, hoặc text không phải số
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v:                      
                    return np.nan
                # Xử lý định dạng: bỏ %, bỏ dấu phẩy
                s = str_v.replace('%', '').replace(',', '').strip()
                if s == '-': return 0.0
                return float(s)
            return np.nan
        except Exception:
            return np.nan

    # Xác định các cột dữ liệu Tuần (Week 1, 2, 3, 4)
    weekly_col_idxs = [3, 4, 5, 6] # Cột D, E, F, G

    # Xác định số lượng Ngày (Days) thực tế có dữ liệu
    date_row_idx = 3 # Dòng chứa "Ngày"
    start_col_idx = -1
    for c in range(2, len(vals[date_row_idx])):
        val = str(vals[date_row_idx][c]).strip()
        if val == "1":
            start_col_idx = c
            break
            
    num_days = 26 # Mặc định nếu không tìm thấy
    if start_col_idx != -1:
        max_day = 1
        for c in range(start_col_idx, len(vals[date_row_idx])):
            val = str(vals[date_row_idx][c]).strip()
            if val.isdigit():
                max_day = max(max_day, int(val))
        num_days = max_day
    else:
        start_col_idx = 6 # Mặc định là cột G nếu không tìm thấy "1"

    cols_to_scan = [start_col_idx + i for i in range(num_days)]

    # --- HÀM TRÍCH XUẤT DỮ LIỆU CHO MỘT HUB ---
    def extract_hub_data(vin_idx, vout_idx, win_idx, wout_idx, tproc_vol_idx, tproc_wgt_idx, ms_idx, ms_rt_idx, bl_idx, lhc_idx, lht_idx, shc_idx, sht_idx):
        # 1. Dữ liệu hàng ngày (Daily)
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
        
        # Vận tải
        data["LH Đúng Giờ"] = [clean_val(lhc_idx, c) - clean_val(lht_idx, c) if pd.notna(clean_val(lhc_idx, c)) else np.nan for c in cols_to_scan]
        data["LH Trễ"] = [clean_val(lht_idx, c) for c in cols_to_scan]
        data["Shuttle Đúng Giờ"] = [clean_val(shc_idx, c) - clean_val(sht_idx, c) if pd.notna(clean_val(shc_idx, c)) else np.nan for c in cols_to_scan]
        data["Shuttle Trễ"] = [clean_val(sht_idx, c) for c in cols_to_scan]
        
        # 2. Dữ liệu Tuần (để tính WOW)
        # Tìm tuần hiện tại (là tuần cuối cùng có dữ liệu Inbound > 0)
        valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
        cw_idx = valid_weeks[-1] if len(valid_weeks) >= 1 else -1
        pw_idx = valid_weeks[-2] if len(valid_weeks) >= 2 else -1
        
        def get_ot_rate(c_idx, t_idx, col_idx):
            if col_idx == -1: return 0
            chuyen = clean_val(c_idx, col_idx)
            tre = clean_val(t_idx, col_idx)
            if pd.isna(chuyen) or chuyen == 0: return 0
            tre = 0 if pd.isna(tre) else tre
            return ((chuyen - tre) / chuyen) * 100
            
        weekly_summary = {
            "cw_vin": clean_val(vin_idx, cw_idx) if cw_idx != -1 else 0, "pw_vin": clean_val(vin_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_vout": clean_val(vout_idx, cw_idx) if cw_idx != -1 else 0, "pw_vout": clean_val(vout_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_ms": clean_val(ms_idx, cw_idx) if cw_idx != -1 else 0, "pw_ms": clean_val(ms_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_bl": clean_val(bl_idx, cw_idx) if cw_idx != -1 else 0, "pw_bl": clean_val(bl_idx, pw_idx) if pw_idx != -1 else 0,
            "cw_lhot": get_ot_rate(lhc_idx, lht_idx, cw_idx), "pw_lhot": get_ot_rate(lhc_idx, lht_idx, pw_idx),
            "cw_shot": get_ot_rate(shc_idx, sht_idx, cw_idx), "pw_shot": get_ot_rate(shc_idx, sht_idx, pw_idx),
        }
        
        return pd.DataFrame(data), weekly_summary

    # --- TRÍCH XUẤT CHO TỪNG HUB VỚI INDEX DÒNG TƯƠNG ỨNG ---
    # Index dòng = Dòng trong Excel - 1
    # HCM Hub: Inbound Vol dòng 5 (idx 4), Outbound Vol dòng 6 (idx 5),...
    data_hcm = extract_hub_data(4, 5, 6, 7, 8, 9, 17, 18, 31, 38, 40, 39, 41)
    
    # BN Hub: Inbound Vol dòng 11 (idx 10), Outbound Vol dòng 12 (idx 11),...
    data_bn = extract_hub_data(10, 11, 12, 13, 14, 15, 19, 20, 32, 47, 49, 48, 50)
    
    return data_hcm, data_bn

# ==========================================
# 3. HÀM BỔ TRỢ (HELPER FUNCTIONS)
# ==========================================
def format_vietnam(number):
    """Định dạng số theo kiểu Việt Nam (dấu chấm phân cách ngàn)."""
    if pd.isna(number) or number == "": return "0"
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    """Tạo HTML cho ô hiển thị WOW (tăng/giảm màu xanh/đỏ)."""
    # Xử lý trường hợp không có dữ liệu tuần trước
    if prev is None or pd.isna(prev) or (prev == 0 and not is_pct):
        cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
        return f"<td style='text-align: center;'>-</td><td class='col-num'>{cur_str}</td><td class='col-num'>-</td>"
        
    diff = cur - prev
    # Tính % thay đổi, hoặc hiệu số nếu là chỉ số % (ví dụ Tỷ lệ OT)
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    
    # Định nghĩa màu sắc và dấu
    if diff > 0:
        bg_color, text_color, sign = "#dcfce7", "#15803d", "+" # Xanh lục
        if inverse: bg_color, text_color = "#fee2e2", "#b91c1c" # Đỏ nếu tăng là xấu (Missort, Backlog)
    elif diff < 0:
        bg_color, text_color, sign = "#fee2e2", "#b91c1c", "" # Đỏ
        if inverse: bg_color, text_color = "#dcfce7", "#15803d" # Xanh lục nếu giảm là tốt
    else:
        bg_color, text_color, sign = "transparent", "#333", "" # Không đổi
        
    # Định dạng chuỗi hiển thị
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    
    return f"""
        <td style='background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'>{wow_str}</td>
        <td class='col-num'>{cur_str}</td>
        <td class='col-num'>{prev_str}</td>
    """

def render_dashboard(df, summary, primary_color):
    """Hàm chính để vẽ giao diện dashboard cho một Hub."""
    if df.empty: return

    # Tính toán các chỉ số MTD (Month-To-Date)
    t_vin = df['Inbound Vol'].sum(skipna=True) 
    t_vout = df['Outbound Vol'].sum(skipna=True) 
    t_tproc_vol = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt = df['Total Process Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    
    # Tính tỷ lệ OT MTD
    lh_total = df['LH Đúng Giờ'].fillna(0).sum() + df['LH Trễ'].fillna(0).sum()
    sh_total = df['Shuttle Đúng Giờ'].fillna(0).sum() + df['Shuttle Trễ'].fillna(0).sum()
    lhot_mtd = (df['LH Đúng Giờ'].fillna(0).sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df['Shuttle Đúng Giờ'].fillna(0).sum() / sh_total * 100) if sh_total > 0 else 0

    # 1. PHẦN CÁC CHỈ SỐ CHÍNH (METRICS)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Outbound (MTD)", format_vietnam(t_vout))
    c3.metric("Xử lý (MTD)", format_vietnam(t_tproc_vol))
    c4.metric("Trọng lượng (MTD)", format_vietnam(t_tproc_wgt))
    c5.metric("Missort (MTD)", format_vietnam(t_ms))
    c6.metric("Backlog (MTD)", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. PHẦN BẢNG SO SÁNH TUẦN (WOW TABLE) - Sử dụng HTML để tùy biến cao
    st.markdown(f"""
    <table class="kpi-table">
        <thead>
            <tr>
                <th>KPI</th>
                <th>Hạng mục</th>
                <th style="width:100px;">WOW</th>
                <th>Tuần này</th>
                <th>Tuần trước</th>
                <th>MTD</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="2" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td>
                <td class="col-metric">Inbound (đơn)</td>
                {get_wow_cell(summary['cw_vin'], summary['pw_vin'])}
                <td class="col-mtd">{format_vietnam(t_vin)}</td>
            </tr>
            <tr>
                <td class="col-metric">Outbound (đơn)</td>
                {get_wow_cell(summary['cw_vout'], summary['pw_vout'])}
                <td class="col-mtd">{format_vietnam(t_vout)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td>
                <td class="col-metric">Missort (đơn)</td>
                {get_wow_cell(summary['cw_ms'], summary['pw_ms'], inverse=True)}
                <td class="col-mtd">{format_vietnam(t_ms)}</td>
            </tr>
            <tr>
                <td class="col-metric">Backlog (đơn)</td>
                {get_wow_cell(summary['cw_bl'], summary['pw_bl'], inverse=True)}
                <td class="col-mtd">{format_vietnam(t_bl)}</td>
            </tr>
            <tr>
                <td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td>
                <td class="col-metric">LH Đúng Giờ (%)</td>
                {get_wow_cell(summary['cw_lhot'], summary['pw_lhot'], is_pct=True)}
                <td class="col-mtd">{lhot_mtd:.2f}%</td>
            </tr>
            <tr>
                <td class="col-metric">Shuttle Đúng Giờ (%)</td>
                {get_wow_cell(summary['cw_shot'], summary['pw_shot'], is_pct=True)}
                <td class="col-mtd">{shot_mtd:.2f}%</td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    # 3. BIỂU ĐỒ SẢN LƯỢNG (SỬ DỤNG PLOTLY)
    st.markdown(f"<h4 style='color: {primary_color};'>1. Biểu Đồ Sản Lượng & Năng Suất</h4>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    
    with col1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_vol, use_container_width=True)
        
    with col2:
        fig_prod_v = go.Figure()
        fig_prod_v.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#38bdf8'))
        fig_prod_v.update_layout(title="Năng suất (Số đơn)", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_prod_v, use_container_width=True)
        
    with col3:
        fig_prod_w = go.Figure()
        fig_prod_w.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#818cf8'))
        fig_prod_w.update_layout(title="Năng suất (Trọng lượng kg)", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_prod_w, use_container_width=True)

    # 4. BIỂU ĐỒ VẬN TẢI (SỬ DỤNG PLOTLY)
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải</h4>", unsafe_allow_html=True)
    
    # Tính toán tổng chuyến
    df["Tổng LH"] = df["LH Đúng Giờ"].fillna(0) + df["LH Trễ"].fillna(0)
    df["Tổng Shuttle"] = df["Shuttle Đúng Giờ"].fillna(0) + df["Shuttle Trễ"].fillna(0)
    
    col4, col5, col6 = st.columns([1, 1, 1])
    
    with col4:
        fig_total = go.Figure()
        fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['Tổng LH'], name="Linehaul", marker_color='#10b981'))
        fig_total.add_trace(go.Bar(x=df['Ngày'], y=df['Tổng Shuttle'], name="Shuttle", marker_color='#3b82f6'))
        fig_total.update_layout(title="Tổng số chuyến xe", barmode='stack', plot_bgcolor='white', legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_total, use_container_width=True)
        
    with col5:
        fig_lh_late = go.Figure()
        fig_lh_late.add_trace(go.Bar(x=df['Ngày'], y=df['LH Trễ'], name="Trễ LH", marker_color='#ef4444'))
        fig_lh_late.update_layout(title="Số chuyến xe trễ Linehaul", plot_bgcolor='white')
        st.plotly_chart(fig_lh_late, use_container_width=True)
        
    with col6:
        fig_sh_late = go.Figure()
        fig_sh_late.add_trace(go.Bar(x=df['Ngày'], y=df['Shuttle Trễ'], name="Trễ Shuttle", marker_color='#f97316'))
        fig_sh_late.update_layout(title="Số chuyến xe trễ Shuttle", plot_bgcolor='white')
        st.plotly_chart(fig_sh_late, use_container_width=True)

    # 5. PHẦN MỞ RỘNG (EXPANDER) ĐỂ XEM DỮ LIỆU THÔ
    with st.expander("🔍 Chi tiết dữ liệu thô (Dạng bảng xoay chiều)"):
        # Xoay chiều bảng để dễ đọc hơn trên web (chuyển Ngày thành cột đầu tiên)
        st.dataframe(df.set_index("Ngày").T, use_container_width=True)

# ==========================================
# 4. GIAO DIỆN CHÍNH (MAIN LAYOUT)
# ==========================================
# Tiêu đề chính của Dashboard
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)

# Gọi hàm lấy dữ liệu (đã được cache)
data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

# Xử lý trường hợp không có dữ liệu
if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu hoặc không có dữ liệu để hiển thị. Vui lòng kiểm tra lại nguồn Feishu Sheet.")
    st.stop() # Dừng chạy các phần tiếp theo

# Tạo các Tab cho từng Hub
tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

# Gọi hàm render cho từng Tab với dữ liệu tương ứng
with tab1:
    # --- ĐÃ FIX LỖI HIỂN THỊ NGƯỢC TẠI ĐÂY ---
    # Tab HCM -> Truyền dữ liệu df_hcm
    render_dashboard(df_hcm, sum_hcm, "#0284c7") 

with tab2:
    # --- ĐÃ FIX LỖI HIỂN THỊ NGƯỢC TẠI ĐÂY ---
    # Tab BN -> Truyền dữ liệu df_bn
    render_dashboard(df_bn, sum_bn, "#059669")
