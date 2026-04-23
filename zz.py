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
    .stApp, [data-testid="stAppViewContainer"] { background-color: #f8fafc !important; }
    button[data-baseweb="tab"] div { color: #1e3a8a !important; font-weight: bold !important; }
    .kpi-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: white; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; }
    .kpi-table th { background-color: #1e3a8a !important; color: #ffffff !important; padding: 14px 10px; text-align: center; border: 1px solid #94a3b8; font-size: 16px; font-weight: 800; }
    .kpi-table td { padding: 12px 10px; border: 1px solid #cbd5e1; font-size: 16px; vertical-align: middle; color: #1e293b; }
    .col-pillar { font-weight: 800; text-align: center; background-color: #f1f5f9 !important; font-size: 17px; }
    .col-metric { font-weight: 700; color: #0f172a !important; }
    .col-num { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 17px; font-weight: 700; }
    .col-mtd { text-align: right; font-family: 'Courier New', Courier, monospace; font-size: 19px; font-weight: 900; background-color: #dcfce7 !important; color: #166534 !important; }
    div[data-testid="metric-container"] { background-color: #ffffff !important; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08); transition: transform 0.2s ease-in-out; border-left: 5px solid #2563eb; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.15); }
    div[data-testid="metric-container"] label { font-size: 17px !important; font-weight: 700 !important; color: #334155 !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 36px !important; font-weight: 900 !important; color: #1e3a8a !important; }
    .main-title { text-align: center; font-weight: 900; color: #0f172a !important; font-size: 46px; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 1.5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
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
        return None

@st.cache_data(ttl=60)
def get_data():
    token = get_tenant_access_token()
    if not token: return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/NIBWsB2ybhcsamtpF3wcbdL0nVb/values/OGehC6!A1:AQ80?valueRenderOption=FormattedValue"
    headers = {"Authorization": f"Bearer {token}"}
    max_retries = 5
    res_data = None
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=30).json()
            if res.get("code") == 0:
                res_data = res
                break
            elif "not ready" in str(res.get("msg")).lower():
                time.sleep(5)
                continue
        except: return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
    if not res_data: return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})
    vals = res_data.get('data', {}).get('valueRange', {}).get('values', [])
    if not vals or len(vals) < 75: return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

    def clean_val(row_idx, col_idx):
        try:
            if row_idx < len(vals) and col_idx < len(vals[row_idx]):
                v = vals[row_idx][col_idx]
                str_v = str(v).strip()
                if v is None or str_v == "" or "#" in str_v or "IF(" in str_v or "=" in str_v: return np.nan
                s = str_v.replace('%', '').replace(',', '').strip()
                return 0.0 if s == '-' else float(s)
            return np.nan
        except: return np.nan

    try:
        weekly_col_idxs = [3, 4, 5, 6]
        date_row_idx = 3
        start_col_idx = -1
        for c in range(2, len(vals[date_row_idx])):
            if str(vals[date_row_idx][c]).strip() == "1":
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
            data["LH Rate (%)"] = [(c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan for c, t in zip(data["Linehaul Chuyến"], data["Linehaul Late"])]
            data["SH Rate (%)"] = [(c - (t if pd.notna(t) else 0)) / c * 100 if pd.notna(c) and c > 0 else np.nan for c, t in zip(data["Shuttle Chuyến"], data["Shuttle Late"])]

            valid_weeks = [idx for idx in weekly_col_idxs if pd.notna(clean_val(vin_idx, idx)) and clean_val(vin_idx, idx) > 0]
            cw_idx, pw_idx = (valid_weeks[-1] if len(valid_weeks) >= 1 else -1), (valid_weeks[-2] if len(valid_weeks) >= 2 else -1)

            def get_rate(num_idx, den_idx, col_idx):
                if col_idx == -1: return 0
                n, d = clean_val(num_idx, col_idx), clean_val(den_idx, col_idx)
                return (n / d * 100) if (d and d > 0) else 0

            summary = {
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
                "cw_cot": get_rate(cot_ontime_idx, cot_total_idx, cw_idx), "pw_cot": get_rate(cot_ontime_idx, cot_total_idx, pw_idx),
            }
            return pd.DataFrame(data), summary

        return extract_hub_data(4, 5, 6, 7, 8, 9, 23, 24, 42, 50, 52, 51, 53, 47, 48), \
               extract_hub_data(10, 11, 12, 13, 14, 15, 25, 26, 43, 59, 61, 60, 62, 56, 57), \
               extract_hub_data(16, 17, 18, 19, 20, 21, 27, 28, 44, 68, 70, 69, 71, 65, 66)
    except: return (pd.DataFrame(), {}), (pd.DataFrame(), {}), (pd.DataFrame(), {})

# 3. GIAO DIỆN CHÍNH
st.markdown("<div class='main-title'>J&T CARGO KPI DASHBOARD</div>", unsafe_allow_html=True)
data_hcm, data_bn, data_sh = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn
df_sh, sum_sh = data_sh

if df_hcm.empty:
    st.warning("Đang tải dữ liệu hoặc lỗi kết nối...")
    st.stop()

def get_last_7_days(df):
    valid = df.dropna(subset=['Inbound Vol'])
    valid = valid[valid['Inbound Vol'] > 0]
    if valid.empty: return df.tail(7).reset_index(drop=True)
    last = valid.index[-1]
    return df.iloc[max(0, last - 6):last+1].reset_index(drop=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📌 HỒ CHÍ MINH (MTD)", "📌 BẮC NINH (MTD)", "📌 SH DC (MTD)",
    "📌 HCM (7 NGÀY)", "📌 BN (7 NGÀY)", "📌 SH DC (7 NGÀY)"
])

def format_vn(n):
    return f"{n:,.0f}".replace(",", ".") if pd.notna(n) and n != "" else ""

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    if pd.isna(cur) and pd.isna(prev): return "<td></td><td class='col-num'></td><td class='col-num'></td>"
    if pd.isna(prev) or (prev == 0 and not is_pct):
        return f"<td>-</td><td class='col-num'>{format_vn(cur) if not is_pct else f'{cur:.2f}%'}</td><td class='col-num'>-</td>"
    diff = cur - prev
    pct = diff if is_pct else ((diff / prev) * 100 if prev > 0 else 0)
    bg, tx, sn = ("#dcfce7", "#15803d", "+") if diff > 0 else (("#fee2e2", "#b91c1c", "") if diff < 0 else ("transparent", "#1e293b", ""))
    if inverse and diff != 0: bg, tx = ("#fee2e2", "#b91c1c") if diff > 0 else ("#dcfce7", "#15803d")
    return f"<td style='background-color:{bg}; color:{tx}; font-weight:900; text-align:center;'>{sn}{pct:.1f}%</td><td class='col-num'>{format_vn(cur) if not is_pct else f'{cur:.2f}%'}</td><td class='col-num'>{format_vn(prev) if not is_pct else f'{prev:.2f}%'}</td>"

def render_dashboard(df, summary, primary_color, period="MTD", show_weekly=True, num_cols=3):
    valid = df.dropna(subset=['Inbound Vol'])
    valid = valid[valid['Inbound Vol'] > 0]
    actual = min(len(valid), num_cols)
    slice_df = valid.tail(actual + 1).reset_index(drop=True)
    d_names = slice_df['Ngày'].tolist()[1:] if len(slice_df) > actual else slice_df['Ngày'].tolist()
    d_display = ["-"] * (num_cols - len(d_names)) + d_names

    def get_d(col, is_pct=False, inv=False):
        v = slice_df[col].tolist()
        cur_v = (v[1:] if len(v) > actual else v)
        prev_v = (v[:-1] if len(v) > actual else [np.nan] + v[:-1])
        pad = num_cols - len(cur_v)
        cur_v, prev_v = [np.nan]*pad + cur_v, [np.nan]*pad + prev_v
        res = []
        for i in range(num_cols):
            c, p = cur_v[i], prev_v[i]
            if pd.isna(c): res.append("<td class='col-num'></td>"); continue
            txt = f"{c:.1f}%" if is_pct else format_vn(c)
            if pd.notna(p):
                dfx = c - p
                clr = ("#15803d" if inv else "#dc2626") if dfx < 0 else (("#dc2626" if inv else "#15803d") if dfx > 0 else "#475569")
                icon = "↓" if dfx < 0 else ("↑" if dfx > 0 else "")
                txt = f"<span style='color:{clr}; font-weight:700;'>{txt} {icon}</span>"
            res.append(f"<td class='col-num' style='background-color:{'#f8fafc' if i%2==0 else '#fff'};'>{txt}</td>")
        return "".join(res)

    t_vin, t_vout, t_vol, t_wgt, t_ms, t_bl = df['Inbound Vol'].sum(), df['Outbound Vol'].sum(), df['Total Process Vol'].sum(), df['Total Process Wgt'].sum(), df['Missort'].sum(), df['Backlog'].sum()
    cot_on, cot_tot = df['COT Ontime'].sum(), df['COT Total'].sum()
    cot_mtd = (cot_on / cot_tot * 100) if cot_tot > 0 else 0
    lh_c, lh_t = df['Linehaul Chuyến'].sum(), df['Linehaul Late'].sum()
    lhot = ((lh_c - lh_t) / lh_c * 100) if lh_c > 0 else 0
    sh_c, sh_t = df['Shuttle Chuyến'].sum(), df['Shuttle Late'].sum()
    shot = ((sh_c - sh_t) / sh_c * 100) if sh_c > 0 else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(f"Inbound ({period})", format_vn(t_vin))
    c2.metric(f"Outbound ({period})", format_vn(t_vout))
    c3.metric(f"Xử lý ({period})", format_vn(t_vol))
    c4.metric("Trọng lượng (Kg)", format_vn(t_wgt))
    c5.metric(f"Missort ({period})", format_vn(t_ms))
    c6.metric(f"Backlog ({period})", format_vn(t_bl))

    h_wow = "<th>WOW</th><th>Tuần này</th><th>Tuần trước</th>" if show_weekly else ""
    d_hd = "".join([f"<th style='background-color:#1e40af;'>{d}</th>" for d in d_display])

    def row(title, rs, colr, name, w_c, w_p, m_v, c_n, pct=False, inv=False, first=False):
        p_td = f'<td rowspan="{rs}" class="col-pillar" style="color:{colr};">{title}</td>' if first else ''
        w_td = get_wow_cell(w_c, w_p, pct, inv) if show_weekly else ''
        m_str = f"{m_v:.1f}%" if pct else format_vn(m_v)
        return f"<tr>{p_td}<td class='col-metric'>{name}</td>{w_td}<td class='col-mtd'>{m_str}</td>{get_d(c_n, pct, inv)}</tr>"

    st.markdown(f"""<table class="kpi-table"><thead><tr><th>KPI</th><th>Hạng mục</th>{h_wow}<th>{period}</th>{d_hd}</tr></thead><tbody>
    {row("Sản Lượng",3,"#0284c7","Inbound",summary['cw_vin'],summary['pw_vin'],t_vin,'Inbound Vol',first=True)}
    {row("",3,"","Outbound",summary['cw_vout'],summary['pw_vout'],t_vout,'Outbound Vol')}
    {row("",3,"","Trọng lượng (kg)",summary['cw_tproc_wgt'],summary['pw_tproc_wgt'],t_wgt,'Total Process Wgt')}
    {row("Chất Lượng",4,"#dc2626","Missort",summary['cw_ms'],summary['pw_ms'],t_ms,'Missort',inv=True,first=True)}
    {row("",4,"","Backlog",summary['cw_bl'],summary['pw_bl'],t_bl,'Backlog',inv=True)}
    {row("",4,"","Đúng COT (đơn)",summary['cw_cot_ontime'],summary['pw_cot_ontime'],cot_on,'COT Ontime')}
    {row("",4,"","% Đúng COT",summary['cw_cot'],summary['pw_cot'],cot_mtd,'COT Rate (%)',pct=True)}
    {row("Vận Tải",2,"#059669","Linehaul Đúng COT %",summary['cw_lhot'],summary['pw_lhot'],lhot,'LH Rate (%)',pct=True,first=True)}
    {row("",2,"","Shuttle Đúng COT %",summary['cw_shot'],summary['pw_shot'],shot,'SH Rate (%)',pct=True)}
    </tbody></table>""", unsafe_allow_html=True)

    # --- CHART ---
    col_a, col_b = st.columns(2)
    with col_a:
        f1 = go.Figure()
        f1.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy', line=dict(color='#0284c7', width=4)))
        f1.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        f1.update_layout(title="Lượng hàng hàng ngày", height=400, margin=dict(t=50,b=20,l=10,r=10))
        st.plotly_chart(f1, use_container_width=True)
    with col_b:
        f2 = go.Figure()
        f2.add_trace(go.Bar(x=df['Ngày'], y=df['COT Rate (%)'], marker_color='#059669', text=[f"{v:.0f}%" if v>0 else "" for v in df['COT Rate (%)']], textposition='outside'))
        f2.update_layout(title="% Sent Vol Ontime", height=400, margin=dict(t=50,b=20,l=10,r=10), yaxis_range=[0,110])
        st.plotly_chart(f2, use_container_width=True)

    # --- BẢN DỮ LIỆU THÔ (RAW DATA) ---
    with st.expander("🔍 Chi tiết dữ liệu thô | 详细数据"):
        raw = df.copy()
        for c in raw.columns:
            if c != "Ngày":
                raw[c] = raw[c].apply(lambda x: f"{x:.1f}%" if (pd.notna(x) and "%" in c) else format_vn(x))
        st.dataframe(raw.set_index("Ngày").T, use_container_width=True)

with tab1: render_dashboard(df_hcm, sum_hcm, "#0284c7", period="MTD")
with tab2: render_dashboard(df_bn, sum_bn, "#059669", period="MTD")
with tab3: render_dashboard(df_sh, sum_sh, "#8b5cf6", period="MTD")
with tab4: render_dashboard(get_last_7_days(df_hcm), sum_hcm, "#0284c7", period="7 Ngày", show_weekly=False, num_cols=7)
with tab5: render_dashboard(get_last_7_days(df_bn), sum_bn, "#059669", period="7 Ngày", show_weekly=False, num_cols=7)
with tab6: render_dashboard(get_last_7_days(df_sh), sum_sh, "#8b5cf6", period="7 Ngày", show_weekly=False, num_cols=7)
