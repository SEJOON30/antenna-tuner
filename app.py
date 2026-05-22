import streamlit as st
import skrf as rf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. 표준 소자 값 리스트 (엔지니어링 표준 수치)
STD_VALUES = [
    1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2,
    10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82, 100
]

def get_nearest_std(val):
    """계산된 소자 값과 가장 가까운 표준 소자 값을 찾아줍니다."""
    if val <= 0:
        return STD_VALUES[0]
    scale = 10 ** np.floor(np.log10(val))
    normalized = val / scale
    nearest_normalized = min(STD_VALUES, key=lambda x: abs(x - normalized))
    result = nearest_normalized * scale
    return round(result, 2)

# 앱 제목 및 소개
st.title("📡 안테나 실전 스마트 멀티밴드 튜닝 시스템")
st.write("기존 소자를 빼고 새 소자를 넣었을 때, 최대 3개의 멀티 밴드 마커가 스미스차트에서 어떻게 움직이는지 실시간으로 검증하세요.")

# 2. 파일 업로더
uploaded_file = st.file_uploader("측정된 안테나 S1P 파일을 선택하세요", type=None)

if uploaded_file is not None:
    try:
        # 파일 읽기 및 네트워크 객체 생성
        file_bytes = uploaded_file.read()
        with open("temp.s1p", "wb") as f:
            f.write(file_bytes)
        
        ntwk_measured = rf.Network("temp.s1p")
        
        # 원본 파일 주파수 정보 한계점 파악
        file_min_f = float(ntwk_measured.f[0] / 1e6)
        file_max_f = float(ntwk_measured.f[-1] / 1e6)

        st.subheader("📊 안테나 기본 정보")
        st.write(f"**S1P 파일 원본 주파수 범위:** {file_min_f:.1f} MHz ~ {file_max_f:.1f} MHz")

        # ---------------------------------------------
        # 🔍 [핵심 추가] 관찰할 스미스차트 주파수 범위 설정 (Start / Stop)
        # ---------------------------------------------
        st.subheader("🔍 관찰할 스미스 차트 주파수 범위 설정 (S1P 범위 내에서 입력)")
        col_range1, col_range2 = st.columns(2)
        with col_range1:
            start_f_mhz = st.number_input(
                "시작 주파수 (Start MHz)", 
                min_value=file_min_f, 
                max_value=file_max_f, 
                value=file_min_f, 
                step=1.0,
                format="%.1f"
            )
        with col_range2:
            stop_f_mhz = st.number_input(
                "종료 주파수 (Stop MHz)", 
                min_value=file_min_f, 
                max_value=file_max_f, 
                value=file_max_f, 
                step=1.0,
                format="%.1f"
            )
            
        if start_f_mhz >= stop_f_mhz:
            st.error("⚠️ 시작 주파수는 종료 주파수보다 작아야 합니다!")
            st.stop()

        # 3. 멀티 주파수 마커 설정 (최대 3개)
        st.subheader("🎯 관찰할 목표 마커 주파수 설정 (최대 3개)")
        num_markers = st.radio("관찰할 밴드(주파수) 개수", [1, 2, 3], index=0, horizontal=True)
        
        freq_list = []
        default_freqs = [
            (start_f_mhz + stop_f_mhz) / 2,
            start_f_mhz + (stop_f_mhz - start_f_mhz) * 0.3,
            start_f_mhz + (stop_f_mhz - start_f_mhz) * 0.7
        ]
        
        cols_freq = st.columns(num_markers)
        for i in range(num_markers):
            with cols_freq[i]:
                f_val = st.number_input(
                    f"마커 #{i+1} 주파수 (MHz)",
                    min_value=file_min_f,
                    max_value=file_max_f,
                    value=round(default_freqs[i], 1),
                    step=0.1,
                    format="%.1f",
                    key=f"freq_mhz_{i}"
                )
                freq_list.append(f_val)
        
        # 4. [기존 소자 세팅] 측정할 때 기판에 끼워져 있던 현재 소자 값 입력
        st.subheader("🛠️ [단계 1] 측정 당시 기판에 장착되어 있던 소자 (고정 입력)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**현재 직렬 소자**")
            current_serial_type = st.radio("현재 직렬 종류", ["없음(직결)", "인덕터 (직렬 L)", "커패시터 (직렬 C)"], key="c_ser")
            if current_serial_type == "인덕터 (직렬 L)":
                current_serial_v = st.number_input("현재 직렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1, key="c_ser_v")
            elif current_serial_type == "커패시터 (직렬 C)":
                current_serial_v = st.number_input("현재 직렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1, key="c_ser_v")
                
        with col2:
            st.write("**현재 병렬 소자**")
            current_shunt_type = st.radio("현재 병렬 종류", ["없음(오픈)", "인덕터 (병렬 L)", "커패시터 (병렬 C)"], key="c_sh")
            if current_shunt_type == "인덕터 (병렬 L)":
                current_shunt_v = st.number_input("현재 병렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1, key="c_sh_v")
            elif current_shunt_type == "커패시터 (병렬 C)":
                current_shunt_v = st.number_input("현재 병렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1, key="c_sh_v")

        # --- 계산 엔진 시작 ---
        f_arr = ntwk_measured.f
        w = 2 * np.pi * f_arr
        z0 = 50.0
        
        # ---------------------------------------------
        # 역산 과정: 전체 주파수 대역에서 기존 소자 성분 제거 (순수 안테나 상태 획득)
        # ---------------------------------------------
        z_measured = ntwk_measured.z[:, 0, 0]
        z_raw_array = z_measured.copy()
        
        if current_shunt_type == "인덕터 (병렬 L)":
            y_raw = 1 / z_raw_array - 1 / (1j * w * (current_shunt_v * 1e-9))
            z_raw_array = 1 / y_raw
        elif current_shunt_type == "커패시터 (병렬 C)":
            y_raw = 1 / z_raw_array - 1j * w * (current_shunt_v * 1e-12)
            z_raw_array = 1 / y_raw
            
        if current_serial_type == "인덕터 (직렬 L)":
            z_raw_array = z_raw_array - 1j * w * (current_serial_v * 1e-9)
        elif current_serial_type == "커패시터 (직렬 C)":
            z_raw_array = z_raw_array - 1 / (1j * w * (current_serial_v * 1e-12))

        # ---------------------------------------------
        # 🤖 AI 최적 튜닝 자동 추천 기능 (마커 #1 주파수 기준으로 이론값 가이드)
        # ---------------------------------------------
        st.subheader("💡 [단계 2] AI 최적 튜닝 추천 값 (마커 #1 주파수 기준)")
        idx_ref = (np.abs(f_arr - (freq_list[0] * 1e6))).argmin()
        w_target_ref = w[idx_ref]
        r_ant = z_raw_array[idx_ref].real
        x_ant = z_raw_array[idx_ref].imag
        
        if r_ant <= 0:
            st.warning("⚠️ 안테나 저항이 비정상적입니다. 소자 값을 확인해 주세요.")
        else:
            if r_ant <= z0:
                tmp = np.sqrt((z0 - r_ant) / r_ant)
                x_shunt = z0 / tmp
                x_serial = x_ant + r_ant * tmp
                req_shunt_c = 1 / (w_target_ref * x_shunt) * 1e12
                if x_serial >= 0:
                    req_serial_l = x_serial / w_target_ref * 1e9
                    st.success(f"🔥 추천 튜닝 ({freq_list[0]:.1f} MHz 기준) ➡️ **[직렬] 인덕터(L) {get_nearest_std(req_serial_l)} nH** / **[병렬] 커패시터(C) {get_nearest_std(req_shunt_c)} pF**")
                else:
                    req_serial_c = -1 / (w_target_ref * x_serial) * 1e12
                    st.success(f"🔥 추천 튜닝 ({freq_list[0]:.1f} MHz 기준) ➡️ **[직렬] 커패시터(C) {get_nearest_std(req_serial_c)} pF** / **[병렬] 커패시터(C) {get_nearest_std(req_shunt_c)} pF**")
            else:
                g_ant = 1 / r_ant
                b_ant = -x_ant / (r_ant**2 + x_ant**2)
                g0 = 1 / z0
                tmp = np.sqrt((g0 - g_ant) / g_ant)
                b_shunt = g_ant * tmp - b_ant
                x_serial = 1 / (g0 * tmp)
                req_serial_l = x_serial / w_target_ref * 1e9
                if b_shunt >= 0:
                    req_shunt_c = b_shunt / w_target_ref * 1e12
                    st.success(f"🔥 추천 튜닝 ({freq_list[0]:.1f} MHz 기준) ➡️ **[직렬] 인덕터(L) {get_nearest_std(req_serial_l)} nH** / **[병렬] 커패시터(C) {get_nearest_std(req_shunt_c)} pF**")
                else:
                    req_shunt_l = -1 / (w_target_ref * b_shunt) * 1e9
                    st.success(f"🔥 추천 튜닝 ({freq_list[0]:.1f} MHz 기준) ➡️ **[직렬] 인덕터(L) {get_nearest_std(req_serial_l)} nH** / **[병렬] 인덕터(L) {get_nearest_std(req_shunt_l)} nH**")

        # ---------------------------------------------
        # 🔄 [단계 3] 변경할 새 매칭 소자 입력 (검증 칸)
        # ---------------------------------------------
        st.subheader("🔄 [단계 3] 변경할 튜닝 값 입력 (수동 미세조정 및 멀티밴드 매칭 확인)")
        col3, col4 = st.columns(2)
        
        with col3:
            st.write("**변경할 직렬 소자**")
            new_serial_type = st.radio("새 직렬 종류", ["없음(직결)", "인덕터 (직렬 L)", "커패시터 (직렬 C)"], key="n_ser")
            if new_serial_type == "인덕터 (직렬 L)":
                new_serial_v = st.number_input("변경할 직렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1, key="n_ser_v")
            elif new_serial_type == "커패시터 (직렬 C)":
                new_serial_v = st.number_input("변경할 직렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1, key="n_ser_v")
                
        with col4:
            st.write("**변경할 병렬 소자**")
            new_shunt_type = st.radio("새 병렬 종류", ["없음(오픈)", "인덕터 (병렬 L)", "커패시터 (병렬 C)"], key="n_sh")
            if new_shunt_type == "인덕터 (병렬 L)":
                new_shunt_v = st.number_input("변경할 병렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1, key="n_sh_v")
            elif new_shunt_type == "커패시터 (병렬 C)":
                new_shunt_v = st.number_input("변경할 병렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1, key="n_sh_v")

        # ---------------------------------------------
        # 정산 과정: 순수 안테나 상태에 유저가 입력한 [변경할 새 소자] 대입하기
        # ---------------------------------------------
        z_tuned = z_raw_array.copy()
        
        if new_serial_type == "인덕터 (직렬 L)":
            z_tuned = z_tuned + 1j * w * (new_serial_v * 1e-9)
        elif new_serial_type == "커패시터 (직렬 C)":
            z_tuned = z_tuned + 1 / (1j * w * (new_serial_v * 1e-12))
            
        if new_shunt_type == "인덕터 (병렬 L)":
            y_tuned = 1 / z_tuned
            y_tuned = y_tuned + 1 / (1j * w * (new_shunt_v * 1e-9))
            z_tuned = 1 / y_tuned
        elif new_shunt_type == "커패시터 (병렬 C)":
            y_tuned = 1 / z_tuned
            y_tuned = y_tuned + 1j * w * (new_shunt_v * 1e-12)
            z_tuned = 1 / y_tuned

        s_tuned = (z_tuned - z0) / (z_tuned + z0)
        
        # 주파수 필터링을 적용하기 위해 새로운 네트워크 슬라이싱 처리
        ntwk_measured_filtered = ntwk_measured[f"{start_f_mhz}mhz-{stop_f_mhz}mhz"]
        
        # 튜닝된 데이터를 임시 네트워크 객체로 랩핑하여 필요한 구간만 슬라이싱
        ntwk_tuned_full = ntwk_measured.copy()
        ntwk_tuned_full.s[:, 0, 0] = s_tuned
        ntwk_tuned_filtered = ntwk_tuned_full[f"{start_f_mhz}mhz-{stop_f_mhz}mhz"]

        # ---------------------------------------------
        # 🎯 주파수별 데이터 수집 및 테이블 출력
        # ---------------------------------------------
        st.subheader("🎯 주파수 마커별 실시간 임피던스(Z) 수치 결과")
        
        marker_colors = ['#FF1493', '#00FF00', '#00FFFF']
        marker_symbols_meas = ['X', 's', '^']
        marker_symbols_tune = ['o', 'D', 'v']
        
        data_rows = []
        marker_points = []

        for idx_m, f_mhz in enumerate(freq_list):
            idx_f = (np.abs(f_arr - (f_mhz * 1e6))).argmin()
            
            z_m = z_measured[idx_f]
            z_t = z_tuned[idx_f]
            s_m = ntwk_measured.s[idx_f, 0, 0]
            s_t = ntwk_tuned_full.s[idx_f, 0, 0]
            
            data_rows.append({
                "마커 번호": f"Marker #{idx_m+1}",
                "주파수 (MHz)": f"{f_mhz:.1f}",
                "측정 당시 (Original)": f"{z_m.real:.2f} + j({z_m.imag:.2f}) Ω",
                "변경 후 (Tuned)": f"{z_t.real:.2f} + j({z_t.imag:.2f}) Ω"
            })
            
            marker_points.append({
                's_meas': s_m,
                's_tune': s_t,
                'freq_str': f"{f_mhz:.1f}MHz"
            })
            
        df_result = pd.DataFrame(data_rows)
        st.table(df_result)

        # 6. 스미스 차트 시각화 (사용자 범위 지정 반영)
        st.subheader(f"📈 Smith Chart ({start_f_mhz:.1f} MHz ~ {stop_f_mhz:.1f} MHz 구간 확대)")
        fig, ax = plt.subplots(figsize=(7, 7))
        
        # 설정한 범위의 구간 궤적만 드로잉
        ntwk_measured_filtered.plot_s_smith(ax=ax, linestyle='--', alpha=0.5, label="Measured Trace (Range)")
        ntwk_tuned_filtered.plot_s_smith(ax=ax, linewidth=2, label="Tuned Trace (Range)")
        
        # 지정 마커 맵핑
        for i, pt in enumerate(marker_points):
            color = marker_colors[i]
            ax.plot(pt['s_meas'].real, pt['s_meas'].imag, marker=marker_symbols_meas[i], 
                    color=color, markersize=8, markeredgecolor='black', linestyle='None',
                    label=f"M#{i+1} Original ({pt['freq_str']})")
            
            ax.plot(pt['s_tune'].real, pt['s_tune'].imag, marker=marker_symbols_tune[i], 
                    color=color, markersize=10, markeredgecolor='black', linestyle='None',
                    label=f"M#{i+1} Tuned ({pt['freq_str']})")
        
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        st.pyplot(fig)

    except Exception as e:
        st.error(f"⚠️ 에러 발생: {e}")
else:
    st.info("📱 스마트폰에서 .s1p 파일을 업로드하면 실전 튜닝 화면이 시작됩니다.")
