def render_dashboard(df, primary_color):
    if df.empty:
        st.info("Chưa có dữ liệu cho Hub này.")
        return

    # --- 1. TÍNH TỔNG MTD (Cho các số lớn hiển thị ở Header) ---
    total_vol = df['Tổng lượng hàng'].sum(skipna=True) 
    total_weight = df['Tổng trọng lượng (Kg)'].sum(skipna=True)
    total_missort = df['Số đơn Missort'].sum(skipna=True)
    total_backlog = df['Backlog tồn đọng'].sum(skipna=True)

    total_xe_dung = df['Xe Đúng COT (Tổng)'].sum(skipna=True)
    total_xe_chay = total_xe_dung + df['Xe Sai COT (Tổng)'].sum(skipna=True)
    final_ontime_rate = (total_xe_dung / total_xe_chay * 100) if total_xe_chay > 0 else 0
    final_missort_rate = (total_missort / total_vol * 100) if total_vol > 0 else 0

    # --- 2. TÍNH WOW (Tuần này vs Tuần trước) ---
    # Lọc bỏ các ngày chưa có dữ liệu ở tương lai
    valid_df = df.dropna(subset=['Tổng lượng hàng'])
    
    # Khởi tạo giá trị WoW mặc định là None (ẩn mũi tên nếu ko đủ data)
    delta_vol = delta_wgt = delta_ms = delta_bl = delta_ot = None
    
    # Cần ít nhất 8 ngày để có thể so sánh tuần này và tuần trước
    if len(valid_df) >= 8:
        # Lấy 7 ngày gần nhất (Tuần này)
        cw = valid_df.iloc[-7:]
        # Lấy 7 ngày trước đó (Tuần trước)
        pw = valid_df.iloc[-14:-7] 
        
        def calc_wow_pct(cur_val, prev_val):
            if prev_val == 0 or pd.isna(prev_val): return 0.0
            return ((cur_val - prev_val) / prev_val) * 100

        # Tính tổng của 7 ngày gần nhất
        cw_vol = cw['Tổng lượng hàng'].sum()
        cw_wgt = cw['Tổng trọng lượng (Kg)'].sum()
        cw_ms = cw['Số đơn Missort'].sum()
        cw_bl = cw['Backlog tồn đọng'].sum()
        cw_xe_chay = cw['Xe Đúng COT (Tổng)'].sum() + cw['Xe Sai COT (Tổng)'].sum()
        cw_ot_rate = (cw['Xe Đúng COT (Tổng)'].sum() / cw_xe_chay * 100) if cw_xe_chay > 0 else 0

        # Tính tổng của 7 ngày trước đó
        pw_vol = pw['Tổng lượng hàng'].sum()
        pw_wgt = pw['Tổng trọng lượng (Kg)'].sum()
        pw_ms = pw['Số đơn Missort'].sum()
        pw_bl = pw['Backlog tồn đọng'].sum()
        pw_xe_chay = pw['Xe Đúng COT (Tổng)'].sum() + pw['Xe Sai COT (Tổng)'].sum()
        pw_ot_rate = (pw['Xe Đúng COT (Tổng)'].sum() / pw_xe_chay * 100) if pw_xe_chay > 0 else 0

        # Xuất chuỗi hiển thị %
        delta_vol = f"{calc_wow_pct(cw_vol, pw_vol):.1f}% WoW"
        delta_wgt = f"{calc_wow_pct(cw_wgt, pw_wgt):.1f}% WoW"
        delta_ms = f"{calc_wow_pct(cw_ms, pw_ms):.1f}% WoW"
        delta_bl = f"{calc_wow_pct(cw_bl, pw_bl):.1f}% WoW"
        delta_ot = f"{(cw_ot_rate - pw_ot_rate):.1f}% WoW" # Tỷ lệ % thì dùng phép trừ trực tiếp

    # --- 3. HIỂN THỊ LÊN GIAO DIỆN ---
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Sản lượng & Trọng lượng: Tăng là Tốt (Màu xanh - normal)
    c1.metric("📦 Tổng Sản Lượng", format_vietnam(total_vol), delta=delta_vol, delta_color="normal")
    c2.metric("⚖️ Tổng Trọng Lượng", format_vietnam(total_weight) + " kg", delta=delta_wgt, delta_color="normal")
    
    # Missort & Backlog: Tăng là XẤU (Streamlit tự đảo màu: Giảm thành Xanh, Tăng thành Đỏ - inverse)
    c3.metric(f"❌ Tổng Missort ({final_missort_rate:.2f}%)", format_vietnam(total_missort), delta=delta_ms, delta_color="inverse")
    c4.metric("📦 Tổng Backlog", format_vietnam(total_backlog), delta=delta_bl, delta_color="inverse")
    
    # Đúng giờ: Tăng là Tốt
    c5.metric("🚚 Tỷ Lệ LH Đúng Giờ", f"{final_ontime_rate:.2f}%", delta=delta_ot, delta_color="normal")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ... (BÊN DƯỚI LÀ CÁC ĐOẠN CODE VẼ BIỂU ĐỒ GIỮ NGUYÊN NHƯ CŨ CỦA BẠN) ...
    st.markdown(f"<h4 style='color: {primary_color};'>1. Đánh giá Sản Lượng & Chất Lượng Phân Loại (Missort)</h4>", unsafe_allow_html=True)
