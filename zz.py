import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
# ... (Giữ nguyên các phần import và cấu hình khác của bạn)

# --- 2. HÀM LẤY DỮ LIỆU TỪ FEISHU --- (Giữ nguyên hàm này)
# ... (Code hàm get_data() và extract_hub_data() của bạn) ...

# --- 3. GIAO DIỆN --- (Bắt đầu thay đổi từ đây)
st.markdown("<h2 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 30px;'>J&T CARGO KPI DASHBOARD</h2>", unsafe_allow_html=True)

data_hcm, data_bn = get_data()
df_hcm, sum_hcm = data_hcm
df_bn, sum_bn = data_bn

if df_hcm.empty and df_bn.empty:
    st.warning("Đang tải dữ liệu...")
    st.stop()

tab1, tab2 = st.tabs(["HỒ CHÍ MINH HUB", "BẮC NINH HUB"])

def format_vietnam(number):
    if pd.isna(number) or number == "": return ""
    return f"{number:,.0f}".replace(",", ".")

def get_wow_cell(cur, prev, is_pct=False, inverse=False):
    # ... (Giữ nguyên hàm này) ...
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
    else:
        bg_color, text_color, sign = "transparent", "#333", ""
    wow_str = f"{sign}{pct:.0f}%" if not is_pct else f"{sign}{diff:.1f}%"
    cur_str = f"{cur:.2f}%" if is_pct else format_vietnam(cur)
    prev_str = f"{prev:.2f}%" if is_pct else format_vietnam(prev)
    return f"<td style='background-color: {bg_color}; color: {text_color}; font-weight: bold; text-align: center;'>{wow_str}</td><td class='col-num'>{cur_str}</td><td class='col-num'>{prev_str}</td>"


# --- HÀM TẠO BIỂU ĐỒ STACKED BAR VỚI TỔNG SỐ LƯỢNG (Mới/Sửa đổi) ---
def add_stacked_bar_with_total_labels(fig, df, x_col, on_time_col, late_col, title, total_label_prefix="Tổng:"):
    # 1. Tính toán tổng số lượng
    # Đảm bảo NaN được xử lý thành 0 để tính toán chính xác
    df_clean = df.copy()
    df_clean[on_time_col] = df_clean[on_time_col].fillna(0)
    df_clean[late_col] = df_clean[late_col].fillna(0)
    df_clean['Total_Vehicles'] = df_clean[on_time_col] + df_clean[late_col]

    # 2. Thêm cột 'Đúng giờ' (Xanh lá)
    # Ta lọc bỏ giá trị 0/NaN bên trong để nhãn đẹp hơn
    fig.add_trace(go.Bar(
        x=df[x_col],
        y=df[on_time_col],
        name="Đúng",
        marker_color='#10b981',  # Xanh lá cây
        text=df[on_time_col].apply(lambda x: f"{int(x)}" if pd.notna(x) and x > 0 else ""),
        textposition='inside',
        textfont=dict(color='white')
    ))

    # 3. Thêm cột 'Trễ' (Đỏ)
    fig.add_trace(go.Bar(
        x=df[x_col],
        y=df[late_col],
        name="Trễ",
        marker_color='#f43f5e',  # Đỏ
        text=df[late_col].apply(lambda x: f"{int(x)}" if pd.notna(x) and x > 0 else ""),
        textposition='inside',
        textfont=dict(color='white')
    ))

    # 4. Thêm cột 'TỔNG' (Tàng hình với nhãn trên cùng)
    # Đây là "trick" để hiển thị tổng số lượng. Cột này có màu trong suốt.
    # Ta lọc chỉ hiển thị nhãn khi tổng > 0
    fig.add_trace(go.Bar(
        x=df_clean[x_col],
        y=df_clean['Total_Vehicles'],
        name="Tổng cộng",
        marker_color='rgba(0,0,0,0)',  # Màu trong suốt hoàn toàn
        hoverinfo='none', # Tắt hover cho cột tàng hình
        text=df_clean['Total_Vehicles'].apply(lambda x: f"{int(x)}" if x > 0 else ""),
        textposition='outside', # Hiển thị phía trên stack
        textfont=dict(color='#1f2937', size=13, font_family='Segoe UI, monospace'), # Nhãn tổng
        showlegend=False # Không hiển thị trong chú thích
    ))

    # Cấu hình Layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        barmode='stack',
        plot_bgcolor='white',
        xaxis=dict(tickangle=45, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#e2e8f0', title="Số lượng xe"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=50, b=80)
    )
    return fig


def render_dashboard(df, summary, primary_color):
    if df.empty: return
    
    # ... (Giữ nguyên các biến t_vin, t_vout, ..., lhot_mtd, shot_mtd của bạn) ...
    t_vin = df['Inbound Vol'].sum(skipna=True)
    t_vout = df['Outbound Vol'].sum(skipna=True)
    t_tproc_vol = df['Total Process Vol'].sum(skipna=True)
    t_tproc_wgt = df['Total Process Wgt'].sum(skipna=True)
    t_ms = df['Missort'].sum(skipna=True)
    t_bl = df['Backlog'].sum(skipna=True)
    lh_total = df['LH Đúng Giờ'].fillna(0).sum() + df['LH Trễ'].fillna(0).sum()
    sh_total = df['Shuttle Đúng Giờ'].fillna(0).sum() + df['Shuttle Trễ'].fillna(0).sum()
    lhot_mtd = (df['LH Đúng Giờ'].fillna(0).sum() / lh_total * 100) if lh_total > 0 else 0
    shot_mtd = (df['Shuttle Đúng Giờ'].fillna(0).sum() / sh_total * 100) if sh_total > 0 else 0
    cw = summary

    # 1. METRICS (Giữ nguyên)
    # ... (Code metrics c1...c6 của bạn) ...
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Inbound (MTD)", format_vietnam(t_vin))
    c2.metric("Outbound (MTD)", format_vietnam(t_vout))
    c3.metric("Xử lý (MTD)", format_vietnam(t_tproc_vol))
    c4.metric("Trọng lượng (MTD)", format_vietnam(t_tproc_wgt))
    c5.metric("Missort (MTD)", format_vietnam(t_ms))
    c6.metric("Backlog (MTD)", format_vietnam(t_bl))
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. WOW TABLE (Giữ nguyên)
    # ... (Code table HTML của bạn) ...
    st.markdown(f"""<table class="kpi-table">
        <thead><tr><th>KPI</th><th>Hạng mục</th><th style="width:100px;">WOW</th><th>Tuần này</th><th>Tuần trước</th><th>MTD</th></tr></thead>
        <tbody>
            <tr><td rowspan="2" class="col-pillar" style="color:#0ea5e9;">Sản Lượng</td><td class="col-metric">Inbound (đơn)</td>{get_wow_cell(cw['cw_vin'], cw['pw_vin'])}<td class="col-mtd">{format_vietnam(t_vin)}</td></tr>
            <tr><td class="col-metric">Outbound (đơn)</td>{get_wow_cell(cw['cw_vout'], cw['pw_vout'])}<td class="col-mtd">{format_vietnam(t_vout)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#ef4444;">Chất Lượng</td><td class="col-metric">Missort (đơn)</td>{get_wow_cell(cw['cw_ms'], cw['pw_ms'], inverse=True)}<td class="col-mtd">{format_vietnam(t_ms)}</td></tr>
            <tr><td class="col-metric">Backlog (đơn)</td>{get_wow_cell(cw['cw_bl'], cw['pw_bl'], inverse=True)}<td class="col-mtd">{format_vietnam(t_bl)}</td></tr>
            <tr><td rowspan="2" class="col-pillar" style="color:#10b981;">Vận Tải</td><td class="col-metric">LH Đúng Giờ (%)</td>{get_wow_cell(cw['cw_lhot'], cw['pw_lhot'], is_pct=True)}<td class="col-mtd">{lhot_mtd:.2f}%</td></tr>
            <tr><td class="col-metric">Shuttle Đúng Giờ (%)</td>{get_wow_cell(cw['cw_shot'], cw['pw_shot'], is_pct=True)}<td class="col-mtd">{shot_mtd:.2f}%</td></tr>
        </tbody></table>""", unsafe_allow_html=True)

    # 3. BIỂU ĐỒ SẢN LƯỢNG & NĂNG SUẤT (Giữ nguyên)
    # ... (Code col1, col2, col3 của bạn) ...
    st.markdown(f"<h4 style='color: {primary_color};'>1. Biểu Đồ Sản Lượng & Năng Suất (Số đơn vs Trọng lượng)</h4>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Inbound Vol'], name="Inbound", fill='tozeroy',
                                      mode='lines+text', text=[format_vietnam(v) if v > 2000 else "" for v in df['Inbound Vol']],
                                      textposition="top center", line=dict(color='#0ea5e9')))
        fig_vol.add_trace(go.Scatter(x=df['Ngày'], y=df['Outbound Vol'], name="Outbound", line=dict(color='#f59e0b', dash='dot')))
        fig_vol.update_layout(title="Inbound & Outbound hàng ngày", plot_bgcolor='white', margin=dict(t=40, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_vol, use_container_width=True)
    with col2:
        fig_prod_v = go.Figure()
        fig_prod_v.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Vol'], marker_color='#38bdf8', opacity=0.8,
                                    text=[format_vietnam(v) for v in df['Total Process Vol']], textposition='outside'))
        fig_prod_v.add_hline(y=df['Total Process Vol'].mean(), line_dash="dash", line_color="red")
        fig_prod_v.update_layout(title="Năng suất (Số đơn)", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_prod_v, use_container_width=True)
    with col3:
        fig_prod_w = go.Figure()
        fig_prod_w.add_trace(go.Bar(x=df['Ngày'], y=df['Total Process Wgt'], marker_color='#818cf8', opacity=0.8,
                                    text=[format_vietnam(v) for v in df['Total Process Wgt']], textposition='outside'))
        fig_prod_w.add_hline(y=df['Total Process Wgt'].mean(), line_dash="dash", line_color="red")
        fig_prod_w.update_layout(title="Năng suất (Trọng lượng kg)", plot_bgcolor='white', margin=dict(t=40, b=10))
        st.plotly_chart(fig_prod_w, use_container_width=True)

    # --- 4. BIỂU ĐỒ VẬN TẢI & HÀNG TỒN (PHẦN ĐÃ SỬA ĐỔI) ---
    st.markdown(f"<h4 style='color: {primary_color};'>2. Quản lý Vận Tải & Hàng Tồn</h4>", unsafe_allow_html=True)
    col4, col5, col6 = st.columns([1, 1, 1])
    
    with col4:
        # Sử dụng hàm mới để tạo Linehaul Stacked Bar với nhãn Tổng
        fig_lh = go.Figure()
        fig_lh = add_stacked_bar_with_total_labels(
            fig_lh, df, 
            x_col='Ngày', 
            on_time_col='LH Đúng Giờ', 
            late_col='LH Trễ', 
            title="Linehaul (LH)"
        )
        st.plotly_chart(fig_lh, use_container_width=True)

    with col5:
        # Sử dụng hàm mới để tạo Shuttle Stacked Bar với nhãn Tổng
        fig_sh = go.Figure()
        fig_sh = add_stacked_bar_with_total_labels(
            fig_sh, df, 
            x_col='Ngày', 
            on_time_col='Shuttle Đúng Giờ', 
            late_col='Shuttle Trễ', 
            title="Shuttle (ST)"
        )
        st.plotly_chart(fig_sh, use_container_width=True)

    with col6:
        # Biểu đồ Backlog (Giữ nguyên)
        fig_bl = px.bar(df, x="Ngày", y="Backlog", title="Backlog tồn đọng", text=df['Backlog'].apply(lambda x: format_vietnam(x) if x > 0 else ""))
        fig_bl.update_traces(marker_color='#f59e0b', textposition='outside')
        fig_bl.update_layout(plot_bgcolor='white', xaxis=dict(tickangle=45), yaxis=dict(title="Số lượng đơn"))
        st.plotly_chart(fig_bl, use_container_width=True)

    with st.expander("🔍 Chi tiết dữ liệu thô"):
        st.dataframe(df.set_index("Ngày").T, use_container_width=True)

# --- PHẦN GỌI TAB (Giữ nguyên) ---
with tab1:
    render_dashboard(df_hcm, sum_hcm, "#0284c7")
with tab2:
    render_dashboard(df_bn, sum_bn, "#059669")
