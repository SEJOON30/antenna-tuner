import streamlit as st
import skrf as rf
import matplotlib.pyplot as plt
import numpy as np

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
st.title("📡 안테나 실전 스마트 튜닝 시스템")
st.write("기존 소자를 입력하면 AI가 최적의 튜닝 값을 자동 추천하고, 이를 직접 대입하여 스미스차트로 검증할 수 있습니다.")

# 2. 파일 업로더
uploaded_file = st.file_uploader("측정된 안테나 S1P 파일을 선택하세요", type=None)

if uploaded_file is not None:
    try:
        # 파일 읽기 및 네트워크 객체 생성
        file_bytes = uploaded_file.read()
        with open("temp.s1p", "wb") as f:
            f.write(file_bytes)
        
        ntwk_measured = rf.Network("temp.s1p")
        
        st.subheader("📊 안테나 기본 정보")
        min_f_mhz = float(ntwk_measured.f[0] / 1e6)
        max_f_mhz = float(ntwk_measured.f[-1] / 1e6)
        default_f_mhz = float((ntwk_measured.f[0] + ntwk_measured.f[-1]) / 2e6)
        st.write(f"**측정 주파수 범위:** {min_f_mhz:.1f} MHz ~ {max_f_mhz:.1f} MHz")

        # 3. 주파수 입력받기
        st.subheader("🎯 목표 마커 주파수 설정")
        freq_mhz = st.number_input(
            "매칭 및 관찰할 주파수를 입력하세요 (MHz)", 
            min_value=min_f_mhz, 
            max_value=max_f_mhz, 
            value=round(default_f_mhz, 1),
            step=0.1,
            format="%.1f"
        )
        
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
        
        idx = (np.abs(f_arr - (freq_mhz * 1e6))).argmin()
        w_target = w[idx]
        
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
        # 🤖 [핵심 추가] AI 최적 튜닝 자동 추천 기능
        # ---------------------------------------------
        st.subheader("💡 [단계 2] AI가 계산한 목표 주파수 최적 튜닝 추천 값")
        r_ant = z_raw_array[idx].real
        x_ant = z_raw_array[idx].imag
        
        if r_ant <= 0:
            st.warning("⚠️ 안테나 저항이 비정상적입니다. 소자 값을 확인해 주세요.")
        else:
            if r_ant <= z0:  # 안테나 저항 < 50옴 (직렬 후 병렬 구조)
                tmp = np.sqrt((z0 - r_ant) / r_ant)
                x_shunt = z0 / tmp
                x_serial = x_ant + r_ant * tmp
                req_shunt_c = 1 / (w_target * x_shunt) * 1e12
                
                if x_serial >= 0:
                    req_serial_l = x_serial / w_target * 1e9
                    st.success(f"🔥 추천 튜닝 ➡️ **[직렬] 인덕터(L) {get_nearest_std(req_serial_l)} nH** / **[병렬] 커패시터(C) {get_nearest_std(req_shunt_c)} pF**")
                else:
                    req_serial_c = -1 / (w_target * x_serial) * 1e12
                    st.success(f"🔥 추천 튜닝 ➡️ **[직렬] 커패시터(C) {get_nearest_std(req_serial_c)} pF** / **[병렬] 커패시터(C) {get_nearest_std(req_shunt_c)} pF**")
            else:  # 안테나 저항 > 50옴 (병렬 후 직렬 구조)
                g_ant = 1 / r_ant
                b_ant = -x_ant / (r_ant**2 + x_ant**2)
                g0 = 1 / z0
                tmp = np.sqrt((g0 - g_ant) / g_ant)
                b_shunt = g_ant * tmp - b_ant
                x_serial = 1 / (g0 * tmp)
                req_serial_l = x_serial / w_target * 1e9
                
                if b_shunt >= 0:
                    req_shunt_c = b_shunt / w_target * 1e12
                    st.success(f"🔥 추천 튜닝 ➡️ **[직렬] 인덕터(L) {get_nearest_std(req_serial_l)} nH** / **[병렬] 커패시터(C) {get_nearest_std(req_shunt_c)} pF**")
                else:
                    req_shunt_l = -1 / (w_target * b_shunt) * 1e9
                    st.success(f"🔥 추천 튜닝 ➡️ **[직렬] 인덕터(L) {get_nearest_std(req_serial_l)} nH** / **[병렬] 인덕터(L) {get_nearest_std(req_shunt_l)} nH**")

        # ---------------------------------------------
        # 🔄 [단계 3] 변경할 새 매칭 소자 입력 (검증 칸)
        # ---------------------------------------------
        st.subheader("🔄 [단계 3] 변경할 튜닝 값 입력 (위의 추천 값을 입력해서 검증해 보세요!)")
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
        ntwk_tuned = ntwk_measured.copy()
        ntwk_tuned.s[:, 0, 0] = s_tuned

        z_measured_marker = z_measured[idx]
        z_tuned_marker = z_tuned[idx]
        s_measured_marker = ntwk_measured.s[idx, 0, 0]
        s_tuned_marker = ntwk_tuned.s[idx, 0, 0]

        # 5. 데이터 출력
        st.subheader("🎯 튜닝 결과 임피던스 비교")
        st.write(f"📍 **{freq_mhz:.1f} MHz** 측정 당시 임피던스: Z = {z_measured_marker.real:.2f} + j({z_measured_marker.imag:.2f}) Ω")
        st.info(f"🔄 **{freq_mhz:.1f} MHz** 소자 변경 후 임피던스: Z = {z_tuned_marker.real:.2f} + j({z_tuned_marker.imag:.2f}) Ω")

        # 6. 스미스 차트 시각화
        st.subheader("📈 Smith Chart (💡 점선: 측정 당시 / 실선: 소자 변경 후)")
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # 측정 당시 안테나 상태 (흐린 점선)
        ntwk_measured.plot_s_smith(ax=ax, linestyle='--', alpha=0.5, label="Measured (Original)")
        ax.plot(s_measured_marker.real, s_measured_marker.imag, 'bx', markersize=6, label="Measured Marker")
        
        # 변경할 새 소자 반영된 안테나 상태 (진한 실선)
        ntwk_tuned.plot_s_smith(ax=ax, linewidth=2, label="Changed (Tuned)")
        ax.plot(s_tuned_marker.real, s_tuned_marker.imag, 'ro', markersize=8, label="Tuned Marker")
        
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"⚠️ 에러 발생: {e}")
else:
    st.info("📱 스마트폰에서 .s1p 파일을 업로드하면 실전 튜닝 화면이 시작됩니다.")
