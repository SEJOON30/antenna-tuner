import streamlit as st
import skrf as rf
import matplotlib.pyplot as plt
import numpy as np

# 앱 제목 및 소개
st.title("📡 안테나 실전 튜닝 시뮬레이터")
st.write("실물 측정 S1P 파일을 고르고, 현재 장착된 소자 값을 입력하여 튜닝 결과를 실시간으로 확인하세요.")

# 1. 파일 업로더 (모든 파일 허용)
uploaded_file = st.file_uploader("측정된 안테나 S1P 파일을 선택하세요", type=None)

if uploaded_file is not None:
    try:
        # 파일 읽기 및 네트워크 객체 생성
        file_bytes = uploaded_file.read()
        with open("temp.s1p", "wb") as f:
            f.write(file_bytes)
        
        # 원본 안테나 데이터 데이터 (소자 없는 상태)
        ntwk_raw = rf.Network("temp.s1p")
        
        st.subheader("📊 안테나 기본 정보")
        min_f_mhz = float(ntwk_raw.f[0] / 1e6)
        max_f_mhz = float(ntwk_raw.f[-1] / 1e6)
        default_f_mhz = float((ntwk_raw.f[0] + ntwk_raw.f[-1]) / 2e6)
        
        st.write(f"**측정 주파수 범위:** {min_f_mhz:.1f} MHz ~ {max_f_mhz:.1f} MHz")

        # 2. [변경] 주파수를 정확히 숫자로 입력받는 칸
        st.subheader("🎯 마커 주파수 설정")
        freq_mhz = st.number_input(
            f"관찰 및 매칭할 목표 주파수를 입력하세요 (단위: MHz)", 
            min_value=min_f_mhz, 
            max_value=max_f_mhz, 
            value=round(default_f_mhz, 1),
            step=0.1,
            format="%.1f"
        )
        
        # 3. 현재 기판에 쓴 매칭 소자 값 직접 입력받기
        st.subheader("🛠️ 현재 매칭 소자 입력 (튜닝)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**1번 소자 (직렬)**")
            serial_type = st.radio("직렬 소자 종류", ["통과 (없음)", "인덕터 (직렬 L)", "커패시터 (직렬 C)"])
            if serial_type == "인덕터 (직렬 L)":
                serial_v = st.number_input("직렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1)
            elif serial_type == "커패시터 (직렬 C)":
                serial_v = st.number_input("직렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1)
                
        with col2:
            st.write("**2번 소자 (병렬)**")
            shunt_type = st.radio("병렬 소자 종류", ["통과 (없음)", "인덕터 (병렬 L)", "커패시터 (병렬 C)"])
            if shunt_type == "인덕터 (병렬 L)":
                shunt_v = st.number_input("병렬 L 값 (nH)", min_value=0.1, max_value=100.0, value=3.3, step=0.1)
            elif shunt_type == "커패시터 (병렬 C)":
                shunt_v = st.number_input("병렬 C 값 (pF)", min_value=0.1, max_value=100.0, value=2.2, step=0.1)

        # 4. 입력된 소자 값을 바탕으로 스미스차트 변환 계산하기
        f_arr = ntwk_raw.f
        w = 2 * np.pi * f_arr
        z0 = 50.0
        
        # 원본 임피던스 추출
        z_current = ntwk_raw.z[:, 0, 0]
        
        # [계산] 직렬 소자 반영
        if serial_type == "인덕터 (직렬 L)":
            z_current = z_current + 1j * w * (serial_v * 1e-9)
        elif serial_type == "커패시터 (직렬 C)":
            z_current = z_current + 1 / (1j * w * (serial_v * 1e-12))
            
        # [계산] 병렬 소자 반영
        if shunt_type == "인덕터 (병렬 L)":
            y_current = 1 / z_current
            y_current = y_current + 1 / (1j * w * (shunt_v * 1e-9))
            z_current = 1 / y_current
        elif shunt_type == "커패시터 (병렬 C)":
            y_current = 1 / z_current
            y_current = y_current + 1j * w * (shunt_v * 1e-12)
            z_current = 1 / y_current

        # 변환된 임피던스를 다시 S-parameter로 변환하여 새로운 네트워크 생성
        s_tuned = (z_current - z0) / (z_current + z0)
        
        ntwk_tuned = ntwk_raw.copy()
        ntwk_tuned.s[:, 0, 0] = s_tuned

        # 선택한 마커 주파수의 현재 값 찾기
        target_freq_hz = freq_mhz * 1e6
        idx = (np.abs(f_arr - target_freq_hz)).argmin()
        
        s_raw_marker = ntwk_raw.s[idx, 0, 0]
        s_tuned_marker = ntwk_tuned.s[idx, 0, 0]
        z_tuned_marker = z_current[idx]

        # 데이터 출력
        st.subheader("🎯 결과 확인")
        st.info(f"📍 **{freq_mhz:.1f} MHz** 입력 소자 반영 후 임피던스: Z = {z_tuned_marker.real:.2f} + j({z_tuned_marker.imag:.2f}) Ω")

        # 5. 스미스 차트 시각화 (원본 vs 튜닝 후 비교)
        st.subheader("📈 Smith Chart (💡 점선: 원본 / 실선: 소자 반영 후)")
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # 원본 안테나 (점선)
        ntwk_raw.plot_s_smith(ax=ax, linestyle='--', alpha=0.5, label="Original (No Match)")
        ax.plot(s_raw_marker.real, s_raw_marker.imag, 'bx', markersize=6, label="Original Marker")
        
        # 소자 반영된 안테나 (실선)
        ntwk_tuned.plot_s_smith(ax=ax, linewidth=2, label="Tuned (With Elements)")
        ax.plot(s_tuned_marker.real, s_tuned_marker.imag, 'ro', markersize=8, label="Tuned Marker (Target)")
        
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"⚠️ 에러 발생: {e}")
else:
    st.info("📱 스마트폰에서 .s1p 파일을 업로드하면 실전 튜닝 화면이 시작됩니다.")
