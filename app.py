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
st.title("📡 안테나 실전 매칭 & 자동 튜닝 추천기")
st.write("측정 당시의 소자 값을 입력하면, 순수 안테나 상태를 역산하여 목표 주파수에서 50Ω 매칭에 필요한 최적의 튜닝 값을 자동으로 계산합니다.")

# 2. 파일 업로더 (모든 파일 허용)
uploaded_file = st.file_uploader("측정된 안테나 S1P 파일을 선택하세요", type=None)

if uploaded_file is not None:
    try:
        # 파일 읽기 및 네트워크 객체 생성
        file_bytes = uploaded_file.read()
        with open("temp.s1p", "wb") as f:
            f.write(file_bytes)
        
        # 측정된 데이터 (현재 소자가 반영되어 있는 상태)
        ntwk_measured = rf.Network("temp.s1p")
        
        st.subheader("📊 안테나 기본 정보")
        min_f_mhz = float(ntwk_measured.f[0] / 1e6)
        max_f_mhz = float(ntwk_measured.f[-1] / 1e6)
        default_f_mhz = float((ntwk_measured.f[0] + ntwk_measured.f[-1]) / 2e6)
        st.write(f"**측정 주파수 범위:** {min_f_mhz:.1f} MHz ~ {max_f_mhz:.1f} MHz")

        # 3. 주파수 입력받기
        st.subheader("🎯 목표 매칭 주파수 설정")
        freq_mhz = st.number_input(
            "매칭(50Ω)을 원하는 주파수를 입력하세요 (MHz)", 
            min_value=min_f_mhz, 
            max_value=max_f_mhz, 
            value=round(default_f_mhz, 1),
            step=0.1,
            format="%.1f"
        )
        
        # 4. [기억용] 측정할 때 기판에 끼워져 있던 현재 소자 값 입력
        st.subheader("🛠️ 측정 당시 장착되어 있던 소자 (기억용)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**현재 직렬 소자**")
            current_serial_type = st.radio("현재 직렬 종류", ["없음(직결)", "인덕터 (직렬 L)", "커패시터 (직렬 C)"], key="c_ser")
            if current_serial_type == "인덕터 (직렬 L)":
                current_serial_v = st.number_input("현재 직렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1)
            elif current_serial_type == "커패시터 (직렬 C)":
                current_serial_v = st.number_input("현재 직렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1)
                
        with col2:
            st.write("**현재 병렬 소자**")
            current_shunt_type = st.radio("현재 병렬 종류", ["없음(오픈)", "인덕터 (병렬 L)", "커패시터 (병렬 C)"], key="c_sh")
            if current_shunt_type == "인덕터 (병렬 L)":
                current_shunt_v = st.number_input("현재 병렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1)
            elif current_shunt_type == "커패시터 (병렬 C)":
                current_shunt_v = st.number_input("현재 병렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1)

        # --- 계산 엔진 시작 ---
        f_arr = ntwk_measured.f
        w = 2 * np.pi * f_arr
        z0 = 50.0
        
        # 선택한 주파수의 인덱스 추출
        target_freq_hz = freq_mhz * 1e6
        idx = (np.abs(f_arr - target_freq_hz)).argmin()
        w_target = w[idx]
        
        # 1) 측정된 s1p 데이터에서 현재 마커의 임피던스
        z_measured_marker = ntwk_measured.z[idx, 0, 0]
        
        # 2) [역산] 현재 소자 값을 빼서 "순수 안테나(Raw) 임피던스" 구해내기
        z_raw = z_measured_marker
        
        # 병렬 소자 제거 (역산)
        if current_shunt_type == "인덕터 (병렬 L)":
            y_raw = 1 / z_raw - 1 / (1j * w_target * (current_shunt_v * 1e-9))
            z_raw = 1 / y_raw
        elif current_shunt_type == "커패시터 (병렬 C)":
            y_raw = 1 / z_raw - 1j * w_target * (current_shunt_v * 1e-12)
            z_raw = 1 / y_raw
            
        # 직렬 소자 제거 (역산)
        if current_serial_type == "인덕터 (직렬 L)":
            z_raw = z_raw - 1j * w_target * (current_serial_v * 1e-9)
        elif current_serial_type == "커패시터 (직렬 C)":
            z_raw = z_raw - 1 / (1j * w_target * (current_serial_v * 1e-12))
            
        # 3) [자동 튜닝 계산] 순수 안테나(z_raw)에서 50옴으로 가기 위한 매칭 소자 자동 계산
        # 여기서는 가장 대중적인 [직렬 소자 -> 병렬 소자] 매칭 알고리즘을 타겟으로 합니다.
        r_ant = z_raw.real
        x_ant = z_raw.imag
        
        st.subheader("🔮 최적 튜닝 값 자동 추천 결과")
        
        if r_ant <= 0:
            st.warning("⚠️ 안테나의 저항 성분이 정상적이지 않습니다. S1P 파일을 확인해 주세요.")
        else:
            # 50옴 매칭을 위한 수식 계산
            # 병렬-직렬 토폴로지 자동 판별 및 계산
            if r_ant <= z0: # 안테나 저항이 50옴보다 작을 때 (보통의 케이스)
                # 병렬 소자 필요 조건 계산
                tmp = np.sqrt((z0 - r_ant) / r_ant)
                x_shunt = z0 / tmp
                x_serial = x_ant + r_ant * tmp
                
                # 병렬 C, 직렬 L 매칭 가정 (가장 일반적)
                req_shunt_c = 1 / (w_target * x_shunt) * 1e12 # pF
                req_serial_l = x_serial / w_target * 1e9 # nH
                
                if req_shunt_c > 0 and req_serial_l > 0:
                    st.success(f"✅ **추천 직렬 소자:** 인덕터(L) **{get_nearest_std(req_serial_l)} nH** (계산값: {req_serial_l:.2f}nH)")
                    st.success(f"✅ **추천 병렬 소자:** 커패시터(C) **{get_nearest_std(req_shunt_c)} pF** (계산값: {req_shunt_c:.2f}pF)")
                else:
                    st.info("💡 기본 토폴로지 외의 매칭 영역입니다. 순수 임피던스 값을 기반으로 수동 튜닝을 권장합니다.")
            else: # 안테나 저항이 50옴보다 클 때
                tmp = np.sqrt((r_ant - z0) / z0)
                # 이 경우에 맞는 매칭 추천
                st.info("💡 안테나 자체 저항이 50Ω보다 큽니다. 기판 특성 및 선로를 재확인하거나 수동 매칭이 필요합니다.")
                
        # 5. 현재 스미스 차트 출력 (유저가 올린 S1P 상태 그대로 보여주기)
        st.subheader("📈 현재 상태 Smith Chart")
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # 현재 측정된 스미스 차트 곡선 그리기
        ntwk_measured.plot_s_smith(ax=ax, linewidth=2, label="Measured S11")
        
        # 유저가 지정한 목표 주파수 마커 표시 (현재 어디 찍혀있는지 확인)
        s_measured_marker = ntwk_measured.s[idx, 0, 0]
        ax.plot(s_measured_marker.real, s_measured_marker.imag, 'ro', markersize=8, label=f"Current Marker ({freq_mhz:.1f} MHz)")
        
        ax.legend()
        st.pyplot(fig)
        
        st.info(f"ℹ️ 현재 {freq_mhz:.1f} MHz 마커 위치의 임피던스: Z = {z_measured_marker.real:.2f} + j({z_measured_marker.imag:.2f}) Ω (목표인 50 + j0 Ω에 가까울수록 좋습니다.)")

    except Exception as e:
        st.error(f"⚠️ 에러 발생: {e}")
else:
    st.info("📱 스마트폰에서 .s1p 파일을 업로드하면 실전 매칭 시뮬레이션이 시작됩니다.")
