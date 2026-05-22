st로 스트림된 가져오기
rf로 skrf 가져오기
numpy를 np로 가져오기
matplotlib 가져오기.pyplot(plt)
matplotlib 가져오기.티커로서의 티커
임시 파일 가져오기
os 가져오기
가져오기 수학
판다를 PD로 가져오기

st.set_page_config(page_title="Pro VNA 분석기 및 튜너", 레이아웃="와이드")

# =========================================================
# 1. 표준 소자값 필터링 및 RF 수학 엔진
# =========================================================
STD_VALUES = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82, 100])

가져오기 get_nearest_std(v):
 v <= 0 또는 math.isinf(v) 또는 math.isan(v)인 경우: 0.0 반환
 STD_VALUES [(np.abs(STD_VALUES - v)).argmin()]을 반환합니다

def calc_LC(X, w):
 X > 0.1인 경우:
 v = (X/w)*1e9
 "인덕터(L)", f"{get_nearest_std(v)}nH", f"{get_nearest_std(v)}를 반환합니다"
 elif X < -0.1:
 v = (-1.0/(w*X))*1e12
"커패시터(C)", f"{get_nearest_std(v)}pF", f"{get_nearest_std(v)}를 반환합니다"
 "없음", "0", 0.0 반환

# =========================================================
# 2. 사이드바 (목표 주파수, 마커, 스케일)
# =========================================================
세인트 sidebar title(" 🎛️ VNA 컨트롤 패널")
사용_sample = st. sidebar.체크박스 ("🧪 샘플 데이터 사용", 값=True)
업로드_파일 = st. sidebar.file_uploader("📂 .s1p 업로드", type=['s1p'])

성 sidebar.header("🎯 매칭 목표 주파수")
target_f = st.sidebar.number_input("Target Freq (GHz)", 값=2.45, 단계=0.01, help="이 주파수를 스미스차트 중앙(ω(50 으로 보냅니다).")

성 sidebar.header("🚩 관찰용 마커 (m1~m9)")
active_markers = {}
i의 범위 (1, 10):
 c_m1, c_m2 = st.sidebar.columns([1, 3])
 if c_m1.checkbox(f"m{i}", value=(i==1), key=f"on{i}"):
 활성_markers[i] = c_m2.number_input(f"m{i} F", 값=2.4+(i*0.05), step=0.01, key=f"f{i}", label_visibility="collapsed")

성 sidebar.header("📊 그래프 스케일 설정")
x_start = st.sidebar.number_input("Start Freq (GHz)), 값=2.0, step=0.1)
x_stop = st.sidebar.number_input("Stop Freq (GHz)), 값=3.0, step=0.1)
x_step = st.sidebar.number_input("X축 단계(GHz)", 값=0.2, 단계=0.05, min_value=0.01)

y_max = st.sidebar.number_input("Y Max (dB)), 값=0.0, 스텝=5.0)
y_min = st.sidebar.number_input("Y Min (dB)), 값=-40.0, 단계=5.0)
y_step = st.sidebar.number_input("Y축 단계(dB)", 값=5.0, 단계=1.0, min_value=1.0)

# =========================================================
# 3. 데이터 로드
# =========================================================
network_orig = 없음
tmp_path = None # ⭐ 에러의 원인 해결! 변수를 미리 생성해둡니다.

사용하는 경우_sample:
 주파수 = RF.주파수(x_start, x_stop, 401, 'ghz')
 z_load = (15 + 3 * (freq.f/1e9)) + 1j * (40 + 80 * (freq.f/1e9 - 2.45))
 network_orig = rf.네트워크(주파수=freq, s=((z_load-50))/(z_load+50)).reshape(-1,1,1))
elif 업로드_파일:
 임시 파일 포함.TMP로 명명된 임시 파일(delete=false, 접미사=.S1P"):
 tmp.write(uploaded_file.getvalue ())
 tmp_path = tmp.name # ⭐ 파일이 업로드 되면 경로를 저장합니다.
 network_orig = rf.네트워크(tmp_path)

# =========================================================
# 4. 메인 화면 UI
# =========================================================
만약 network_orig:
 st.title("📡 Pro VNA 분석기 및 튜너")

 idx_t = (np.abs(network_orig.f/1e9 - target_f)).argmin ()
 tz = network_orig.z[idx_t,0,0]
 ts = network_orig.s[idx_t,0,0]
 t_db = 20*np.log10(np.max([np.abs(ts), 1e-10]))
 t_vswr = (1+np.abs(ts))/(1-np.abs(ts)) if np.abs(ts) < 0.99 else 99

 st.header(f"📌 단계 1: 기본 상태")
    st.success(f"**★ Target ({target_f} GHz)** | S11: **{t_db:.2f} dB** | VSWR: **{t_vswr:.2f}** | Z: **{tz.real:.1f}{tz.imag:+.1f}j Ω**")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 S11 그래프")
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        ax1.plot(network_orig.f/1e9, 20*np.log10(np.abs(network_orig.s[:,0,0])), color='gray', label='Default')
        
        ax1.plot(target_f, t_db, marker='*', color='green', markersize=12, zorder=5)
        ax1.text(target_f, t_db+1.5, 'Target', color='green', weight='bold', ha='center')
        for i, fv in active_markers.items():
            idx = (np.abs(network_orig.f/1e9 - fv)).argmin()
            db_val = 20*np.log10(np.abs(network_orig.s[idx,0,0]))
            ax1.plot(fv, db_val, 'rv'); ax1.text(fv, db_val-2.5, f'm{i}', color='red')
            
        ax1.set_xlim(x_start, x_stop)
        ax1.set_ylim(y_min, y_max)
        ax1.xaxis.set_major_locator(ticker.MultipleLocator(x_step))
        ax1.yaxis.set_major_locator(ticker.MultipleLocator(y_step))
        ax1.grid(True, which='both', linestyle='--')
        st.pyplot(fig1)

    with col2:
        st.subheader("🎯 스미스차트")
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        network_orig.plot_s_smith(ax=ax2, color='gray')
        
        ax2.plot([ts.real], [ts.imag], marker='*', color='green', markersize=12, zorder=5)
        ax2.text(ts.real, ts.imag, ' Target', color='green', weight='bold')
        for i, fv in active_markers.items():
            idx = (np.abs(network_orig.f/1e9 - fv)).argmin()
            ax2.plot([network_orig.s[idx,0,0].real], [network_orig.s[idx,0,0].imag], 'ro')
        st.pyplot(fig2)

    st.markdown("---")
    st.header(f"💡 단계 2: AI 매칭 추천 (★ Target {target_f} GHz 기준)")
    target_topo = st.selectbox("추천받을 매칭 구조 선택", ["Shunt(1단) - Series(2단)", "Series(1단) - Shunt(2단)", "Pi-Match (Shu-Ser-Shu)", "T-Match (Ser-Shu-Ser)"])
    
    RL, XL = tz.real, tz.imag
    w = 2 * math.pi * (target_f * 1e9); Z0 = 50.0

    def calculate_exact_match(topo, RL, XL, w, Z0):
        c1_t, c1_v = "None", 0.0
        c2_t, c2_v = "None", 0.0
        c3_t, c3_v = "None", 0.0
        
        try:
            if RL <= 0: return "에러: R값이 0 이하입니다.", c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
            
            if topo == "Shunt(1단) - Series(2단)":
                if RL >= Z0: return "⚠️ R > 50Ω 조건에서는 Series-Shunt를 권장합니다.", c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
                Q = math.sqrt(Z0/RL - 1)
                X_ser = Q * RL - XL
                X_shu = -Z0 / Q
                c1_t, v1_str, c1_v = calc_LC(X_shu, w)
                c2_t, v2_str, c2_v = calc_LC(X_ser, w)
                msg = f"✅ 타겟 주파수 50Ω 안착 추천값: 1단(Shunt) **{v1_str}** | 2단(Series) **{v2_str}**"
                return msg, c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
                
            elif topo == "Series(1단) - Shunt(2단)":
                GL = RL / (RL**2 + XL**2)
                BL = -XL / (RL**2 + XL**2)
                if GL >= 1/Z0: return "⚠️ R < 50Ω 조건에서는 Shunt-Series를 권장합니다.", c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
                Q = math.sqrt((1/Z0)/GL - 1)
                B_shu = Q * GL - BL
                X_shu = -1.0 / B_shu if B_shu != 0 else 0
                X_ser = Q * Z0
                c1_t, v1_str, c1_v = calc_LC(X_ser, w)
                c2_t, v2_str, c2_v = calc_LC(X_shu, w)
                msg = f"✅ 타겟 주파수 50Ω 안착 추천값: 1단(Series) **{v1_str}** | 2단(Shunt) **{v2_str}**"
                return msg, c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
                
            elif topo == "Pi-Match (Shu-Ser-Shu)":
                Rv = 10.0
                GL = RL / (RL**2 + XL**2)
                BL = -XL / (RL**2 + XL**2)
                if GL >= 1/Rv: 
                    Rv = 1.0 / (GL * 1.1)
                Q2 = math.sqrt((1/Rv)/GL - 1)
                X_shu3 = -1.0 / (Q2 * GL - BL)
                X_ser2_load = Q2 * Rv
                Q1 = math.sqrt(Z0/Rv - 1)
                X_ser2_source = Q1 * Rv
                X_shu1 = -Z0 / Q1
                c1_t, v1_str, c1_v = calc_LC(X_shu1, w)
                c2_t, v2_str, c2_v = calc_LC(X_ser2_load + X_ser2_source, w)
                c3_t, v3_str, c3_v = calc_LC(X_shu3, w)
                msg = f"✅ 추천(Pi): 1단(Shu) **{v1_str}** | 2단(Ser) **{v2_str}** | 3단(Shu) **{v3_str}**"
                return msg, c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
                
            elif topo == "T-Match (Ser-Shu-Ser)":
                Rv = 200.0
                if RL >= Rv: 
                    Rv = RL * 1.1
                Q2 = math.sqrt(Rv/RL - 1)
                X_ser3 = Q2 * RL - XL
                B_shu2_load = Q2 / Rv
                Q1 = math.sqrt(Rv/Z0 - 1)
                X_ser1 = Q1 * Z0
                B_shu2_source = Q1 / Rv
                c1_t, v1_str, c1_v = calc_LC(X_ser1, w)
                c2_t, v2_str, c2_v = calc_LC(-1.0 / (B_shu2_load + B_shu2_source), w)
                c3_t, v3_str, c3_v = calc_LC(X_ser3, w)
                msg = f"✅ 추천(T): 1단(Ser) **{v1_str}** | 2단(Shu) **{v2_str}** | 3단(Ser) **{v3_str}**"
                return msg, c1_t, c1_v, c2_t, c2_v, c3_t, c3_v
                
        except Exception: 
            return "⚠️ 임피던스 계산 범위를 초과했습니다.", c1_t, c1_v, c2_t, c2_v, c3_t, c3_v

    rec_msg, rec_c1_t, rec_c1_v, rec_c2_t, rec_c2_v, rec_c3_t, rec_c3_v = calculate_exact_match(target_topo, RL, XL, w, Z0)
    st.success(rec_msg)

    st.markdown("---")
    st.header("🛠️ 단계 3: 튜닝 시뮬레이션 적용")
    si_col = st.columns(3)
    
    with si_col[0]: 
        t1 = st.selectbox("1단 타입", ["None", "Inductor (L)", "Capacitor (C)"], index=["None", "Inductor (L)", "Capacitor (C)"].index(rec_c1_t))
        v1 = st.number_input("1단 값", value=float(rec_c1_v), step=0.1)
    with si_col[1]:
        t2 = st.selectbox("2단 타입", ["None", "Inductor (L)", "Capacitor (C)"], index=["None", "Inductor (L)", "Capacitor (C)"].index(rec_c2_t))
        v2 = st.number_input("2단 값", value=float(rec_c2_v), step=0.1)
    with si_col[2]:
        t3 = st.selectbox("3단 타입", ["None", "Inductor (L)", "Capacitor (C)"], index=["None", "Inductor (L)", "Capacitor (C)"].index(rec_c3_t))
        v3 = st.number_input("3단 값", value=float(rec_c3_v), step=0.1)

    media = rf.media.DefinedGammaZ0(network_orig.frequency, z0=50.0)
    def make_n(pos, t, v):
        n = media.thru()
        if v > 0:
            if pos == "ser": n = media.inductor(v*1e-9) if t == "Inductor (L)" else media.capacitor(v*1e-12)
            else: n = media.shunt_inductor(v*1e-9) if t == "Inductor (L)" else media.shunt_capacitor(v*1e-12)
        return n

    if target_topo == "Shunt(1단) - Series(2단)": network_pred = make_n("shu", t1, v1) ** make_n("ser", t2, v2) ** network_orig
    elif target_topo == "Series(1단) - Shunt(2단)": network_pred = make_n("ser", t1, v1) ** make_n("shu", t2, v2) ** network_orig
    elif target_topo == "Pi-Match (Shu-Ser-Shu)": network_pred = make_n("shu", t1, v1) ** make_n("ser", t2, v2) ** make_n("shu", t3, v3) ** network_orig
    else: network_pred = make_n("ser", t1, v1) ** make_n("shu", t2, v2) ** make_n("ser", t3, v3) ** network_orig
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        ax3.plot(network_orig.f/1e9, 20*np.log10(np.abs(network_orig.s[:,0,0])), color='gray', ls='--', alpha=0.5, label='Before')
        ax3.plot(network_pred.f/1e9, 20*np.log10(np.abs(network_pred.s[:,0,0])), color='blue', lw=2, label='After')
        
        tz_pred = network_pred.z[idx_t,0,0]; ts_pred = network_pred.s[idx_t,0,0]
        t_db_pred = 20*np.log10(np.max([np.abs(ts_pred), 1e-10]))
        ax3.plot(target_f, t_db_pred, marker='*', color='blue', markersize=14, zorder=5)
        ax3.text(target_f, t_db_pred+1.5, 'Target (Matched)', color='blue', weight='bold', ha='center')
        
        for i, fv in active_markers.items():
            idx = (np.abs(network_pred.f/1e9 - fv)).argmin()
            db_val = 20*np.log10(np.max([np.abs(network_pred.s[idx,0,0]), 1e-10]))
            ax3.plot(fv, db_val, 'bv'); ax3.text(fv, db_val-2.5, f'm{i}', color='blue')
            
        ax3.set_xlim(x_start, x_stop); ax3.set_ylim(y_min, y_max)
        ax3.xaxis.set_major_locator(ticker.MultipleLocator(x_step))
        ax3.yaxis.set_major_locator(ticker.MultipleLocator(y_step))
        ax3.grid(True, which='both', linestyle='--'); ax3.legend(); st.pyplot(fig3)
        
    with col_r2:
        fig4, ax4 = plt.subplots(figsize=(6, 4))
        network_orig.plot_s_smith(ax=ax4, color='gray', ls='--', alpha=0.5)
        network_pred.plot_s_smith(ax=ax4, color='blue', lw=2)
        
        ax4.plot([ts_pred.real], [ts_pred.imag], marker='*', color='blue', markersize=14, zorder=5)
        
        for i, fv in active_markers.items():
            idx = (np.abs(network_pred.f/1e9 - fv)).argmin()
            ax4.plot([network_pred.s[idx,0,0].real], [network_pred.s[idx,0,0].imag], 'bo')
        st.pyplot(fig4)
        
    st.markdown("##### 📝 주요 주파수 매칭 전/후 비교")
    comp_data = []
    
    tz_b = network_orig.z[idx_t,0,0]; tz_a = network_pred.z[idx_t,0,0]
    comp_data.append({
        "구분": "★ Target",
        "주파수 (GHz)": f"{target_f:.3f}",
        "S11 Before (dB)": f"{t_db:.2f}",
        "S11 After (dB)": f"{t_db_pred:.2f}",
        "Z Before (Ω)": f"{tz_b.real:.1f}{tz_b.imag:+.1f}j",
        "Z After (Ω)": f"{tz_a.real:.1f}{tz_a.imag:+.1f}j"
    })
    
    for i, fv in active_markers.items():
        idx_b = (np.abs(network_orig.f/1e9 - fv)).argmin()
        idx_a = (np.abs(network_pred.f/1e9 - fv)).argmin()
        db_b = 20*np.log10(np.max([np.abs(network_orig.s[idx_b,0,0]), 1e-10]))
        db_a = 20*np.log10(np.max([np.abs(network_pred.s[idx_a,0,0]), 1e-10]))
        zb, za = network_orig.z[idx_b,0,0], network_pred.z[idx_a,0,0]
        comp_data.append({"구분": f"Marker {i}", "주파수 (GHz)": f"{fv:.3f}", "S11 Before (dB)": f"{db_b:.2f}", "S11 After (dB)": f"{db_a:.2f}", "Z Before (Ω)": f"{zb.real:.1f}{zb.imag:+.1f}j", "Z After (Ω)": f"{za.real:.1f}{za.imag:+.1f}j"})
    
    st.table(pd.DataFrame(comp_data))

# ⭐ 에러 원인 해결 (tmp_path 가 미리 정의되어 있으므로 에러 없음)
if tmp_path and os.path.exists(tmp_path):
    try: os.remove(tmp_path)
    except: pass
