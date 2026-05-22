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
    # 입력값의 자릿수(scale) 계산
    scale = 10 ** np.floor(np.log10(val))
    normalized = val / scale
    
    # 가장 가까운 표준 값 찾기
    nearest_normalized = min(STD_VALUES, key=lambda x: abs(x - normalized))
    result = nearest_normalized * scale
    return round(result, 2)

# 앱 제목 및 소개
st.title("📡 안테나 매칭 및 튜닝 시뮬레이터")
st.write("S1P 파일을 업로드하여 스미스 차트를 확인하고 매칭 소자 값을 계산하세요.")

# 2. 파일 업로더 (type=None으로 설정하여 핸드폰/태블릿에서도 완벽 지원!)
uploaded_file = st.file_uploader("안테나 S1P 파일을 선택하세요", type=None)

if uploaded_file is not None:
    try:
        # 파일 읽기 및 네트워크 객체 생성
        file_bytes = uploaded_file.read()
        with open("temp.s1p", "wb") as f:
            f.write(file_bytes)
        
        ntwk = rf.Network("temp.s1p")
        
        # 기본 정보 출력
        st.subheader("📊 안테나 기본 정보")
        st.write(f"**주파수 대역:** {ntwk.f[0]/1e6:.1f} MHz ~ {ntwk.f[-1]/1e6:.1f} MHz")
        st.write(f"**데이터 포인트 개수:** {len(ntwk)} 개")

        # 마커 주파수 선택 (매칭할 타겟 주파수)
        freq_mhz = st.slider(
            "매칭할 목표 주파수를 선택하세요 (MHz)", 
            min_value=float(ntwk.f[0]/1e6), 
            max_value=float(ntwk.f[-1]/1e6), 
            value=float((ntwk.f[0]+ntwk.f[-1])/2e6),
            step=1.0
        )
        
        # 선택한 주파수의 인덱스 찾기
        target_freq_hz = freq_mhz * 1e6
        idx = (np.abs(ntwk.f - target_freq_hz)).argmin()
        s_target = ntwk.s[idx, 0, 0]
        z_target = ntwk.z0[idx, 0] * (1 + s_target) / (1 - s_target)
        
        st.info(f"🎯 선택한 {freq_mhz:.1f} MHz에서의 임피던스: Z = {z_target.real:.2f} + j({z_target.imag:.2f}) Ω")

        # 3. 간단한 매칭 가이드 및 추천 로직
        st.subheader("💡 추천 매칭 소자 (가장 가까운 표준값)")
        
        r = z_target.real
        x = z_target.imag
        w = 2 * np.pi * target_freq_hz
        z0 = 50.0 # 기준 임피던스
        
        if x < 0: # 정전용량성 (C성분) -> 직렬 인덕터 필요
            required_l = -x / w * 1e9 # nH 단위
            std_l = get_nearest_std(required_l)
            st.success(f"➡️ **직렬 인덕터(L) 추천:** 계산값 {required_l:.2f} nH ➡️ **표준 소자 값: {std_l} nH**")
        elif x > 0: # 유도성 (L성분) -> 직렬 커패시터 필요
            required_c = 1 / (w * x) * 1e12 # pF 단위
            std_c = get_nearest_std(required_c)
            st.success(f"➡️ **직렬 커패시터(C) 추천:** 계산값 {required_c:.2f} pF ➡️ **표준 소자 값: {std_c} pF**")
        else:
            st.write("이미 50Ω 매칭에 가깝거나 순수 저항 성분만 존재합니다.")

        # 4. 스미스 차트 시각화 (에러가 나던 r=0, c=0 부분을 완벽히 제거했습니다!)
        st.subheader("📈 Smith Chart")
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # 에러 수정된 부분
        ntwk.plot_s_smith(ax=ax, label="Antenna S11")
        
        # 선택한 주파수 포인트에 마커 찍기
        ax.plot(s_target.real, s_target.imag, 'ro', markersize=8, label=f"Target ({freq_mhz:.1f} MHz)")
        ax.legend()
        
        st.pyplot(fig)

    except Exception as e:
        st.error(f"⚠️ 파일을 분석하는 중에 오류가 발생했습니다: {e}")
        st.write("정상적인 S1P(Touchstone) 파일인지 확인해 주세요.")
else:
    st.info("📱 스마트폰이나 PC에서 .s1p 파일을 업로드하면 분석이 시작됩니다.")
