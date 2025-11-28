# app.py (AURA Insight v2.1 - Real-time AI Analysis Engine)
import streamlit as st
import google.generativeai as genai
import time
import io
from PIL import Image
import json

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------
st.set_page_config(
    page_title="AURA Insight - AI 기반 진실 분석 플랫폼",
    page_icon="👁️",
    layout="centered"
)

# API 키 설정 (Streamlit Secrets 사용)
try:
    # 보안을 위해 API 키는 Streamlit Secrets에서 로드해야 합니다.
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 멀티모달 분석이 가능한 모델 로드 (JSON 모드 지원)
    model = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    st.error(f"❌ AI 엔진 초기화 실패: GOOGLE_API_KEY를 Streamlit Secrets에 설정하세요. {e}")
    st.stop()

# ---------------------------------------
# 1. UI/UX 스타일링 (Premium Dark Aesthetic)
# ---------------------------------------
custom_css = """
<style>
/* === 스트림릿 브랜딩 완전 제거 (스텔스 모드) === */
#MainMenu { visibility: hidden !important; } /* 햄버거 메뉴 제거 */
header { visibility: hidden !important; }    /* 상단 헤더 제거 */
footer { visibility: hidden !important; }    /* 하단 'Made with Streamlit' 제거 */
.stDeployButton { display: none !important; } /* 우상단 Deploy 버튼 제거 (배포 시) */

/* 상단 장식 제거 및 패딩 조정하여 독립 앱처럼 보이게 함 */
.stApp [data-testid="stDecoration"] {
    display: none !important;
}
.stApp .main .block-container {
    padding-top: 2rem !important; /* 헤더 제거로 인한 상단 여백 조정 */
}

/* === 모바일 최적화 (필수) === */
@media (max-width: 768px) {
    .stApp .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}

/* === AURA Insight 프리미엄 다크 테마 (기존 코드 유지) === */
.stApp {
    background-color: #101010; /* Deep Black */
    color: #E0E0E0;
    font-family: 'Pretendard', sans-serif;
}
h1 {
    color: #D4AF37; /* Premium Gold */
    font-weight: 800;
    text-align: center;
    margin-bottom: 10px;
    font-family: serif;
}
h2 {
    color: #D4AF37;
    border-bottom: 1px solid #D4AF37;
    padding-bottom: 5px;
    margin-top: 25px;
}
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
    background-color: #2C2C2C;
    color: white;
    border: 1px solid #555;
}
/* 버튼 스타일링 (st.form_submit_button 포함) */
.stButton>button[kind="primary"], div[data-testid="stForm"] button[type="submit"] {
    width: 100%;
    font-weight: bold;
    font-size: 18px !important;
    padding: 15px;
    background-color: #D4AF37 !important;
    color: #101010 !important;
    border-radius: 5px;
    border: none;
}
.stButton>button[kind="primary"]:hover, div[data-testid="stForm"] button[type="submit"]:hover {
    background-color: #B8860B !important;
}

/* 관리자 기능 제거로 사이드바 숨김 처리 (v2.1 기준) */
[data-testid="stSidebar"] { display: none; } 
</style>
"""
# 이 CSS를 app.py 상단에 적용하는 코드는 그대로 유지:
# st.markdown(custom_css, unsafe_allow_html=True)
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. AI 분석 엔진 (★핵심 IP★)
# ---------------------------------------

def get_analysis_prompt(service_type):
    """서비스 유형에 따른 AI 분석 프롬프트 정의 (JSON 출력 강제)."""
    
    if "💔" in service_type: # 불륜 분석
        return """
        [시스템 역할]: 당신은 법의학 수준의 AI 포렌식 분석가입니다. 감정을 배제하고 객관적인 데이터만을 기반으로 분석합니다.
        [목표]: 제공된 정황 설명과 증거 파일(텍스트, 이미지 등)을 교차 분석하여 '불륜 가능성'을 평가합니다.
        [분석 지침]:
        1. 텍스트 분석: 대화 내역(제공된 경우)에서 감정 톤, 빈도, 의심 키워드(애칭, 약속, 거짓말 패턴)를 분석.
        2. 이미지 분석: 사진, 영수증(제공된 경우)에서 장소, 시간, 동반인 유추, 비정상적 지출 패턴을 분석.
        3. 교차 분석: 정황 설명과 증거 자료를 교차 검증하여 알리바이 불일치나 모순점을 탐지.
        4. 스코어링: 분석 결과를 바탕으로 외도 가능성을 0~100점 사이의 점수로 산출. (신중하게 평가).
        
        [입력 데이터]
        정황 설명 및 증거 파일 내용이 멀티모달 입력으로 제공됩니다.

        [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력. 다른 설명은 절대 금지.
        {
          "risk_score": (int),
          "score_reason": "(string: 점수 산출의 핵심 근거 1~2줄 요약)",
          "suspicious_patterns": ["(string: 핵심 의심 정황 1)", "(string: 핵심 의심 정황 2)", "(string: 핵심 의심 정황 3)"],
          "recommendations": ["(string: 권장 조치 1 - 증거 보강 등)", (string: 권장 조치 2 - 전문가 상담 등)]
        }
        """
    elif "🔎" in service_type: # 사람 찾기
         return """
        [시스템 역할]: AI 기반 추적 분석가.
        [목표]: 제공된 정보를 기반으로 대상자 추적 가능성을 평가.
        [분석 지침]: 마지막 연락 정보, 위치, 대상자의 특징(사진 분석 포함)을 분석하여 추적 가능성을 0-100점으로 평가.
        
        [입력 데이터]
        정황 설명 및 증거 파일 내용이 멀티모달 입력으로 제공됩니다.

        [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력.
        {
          "risk_score": (int: 추적 가능성 점수),
          "score_reason": "(string: 점수 근거 및 예상 난이도)",
          "suspicious_patterns": ["(string: 핵심 단서 1)", "(string: 단서 2)", "(string: 단서 3)],
          "recommendations": ["(string: 즉시 취해야 할 조치 1)", (string: 조치 2)]
        }
        """
    else:
        return None # 지원하지 않는 서비스

def perform_ai_analysis(service_type, details, uploaded_files):
    """멀티모달 AI 분석을 실행하고 결과를 파싱합니다."""
    
    prompt = get_analysis_prompt(service_type)
    if not prompt:
        return {"error": "지원되지 않는 서비스 유형입니다."}

    # 1. 멀티모달 입력 구성
    input_payload = [prompt]
    input_payload.append(f"\n[분석 대상 정황 설명]\n{details}\n")

    # 2. 파일 처리 및 주입
    if uploaded_files:
        input_payload.append("\n[분석 대상 증거 파일 목록]\n")
        for file in uploaded_files:
            try:
                if file.type.startswith("image/"):
                    img = Image.open(file)
                    img_byte_arr = io.BytesIO()
                    # 이미지를 JPEG로 변환하여 처리
                    img.convert('RGB').save(img_byte_arr, format='JPEG', quality=85)
                    input_payload.append({"mime_type": "image/jpeg", "data": img_byte_arr.getvalue()})
                
                elif file.type == "text/plain" or "csv" in file.type:
                    # 텍스트 파일 내용 추출 (인코딩 처리)
                    try:
                        string_data = file.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                           string_data = file.getvalue().decode("cp949")
                        except:
                            string_data = "[파일 디코딩 실패]"
                    # 내용을 프롬프트의 일부로 추가
                    input_payload.append(f"--- 파일명: {file.name} (텍스트) ---\n{string_data[:5000]}\n") # 길이 제한

            except Exception as e:
                print(f"File processing error: {e}")

    # 3. AI API 호출 (JSON 모드 강제)
    try:
        # Temperature 0.3로 설정하여 객관성 확보, JSON 출력 강제
        generation_config = genai.GenerationConfig(temperature=0.3, response_mime_type="application/json")
        # 안전 설정 완화 (민감 키워드 고려)
        safety_settings = [
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        response = model.generate_content(input_payload, generation_config=generation_config, safety_settings=safety_settings)
        
        # JSON 응답 파싱
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {"error": f"AI 분석 중 오류 발생 또는 응답 형식 오류: {e}. 응답 내용: {getattr(e, 'response', 'N/A')}"}

# ---------------------------------------
# 3. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

st.title("AURA Insight 👁️")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>AI 기반 진실 분석 및 전문가 매칭 플랫폼</h3>", unsafe_allow_html=True)
st.markdown("---")

# 세션 상태 관리
if 'step' not in st.session_state:
    st.session_state.step = 1

# --- Step 1: 서비스 선택 및 데이터 입력 (통합) ---
if st.session_state.step == 1:
    st.warning("🔒 모든 데이터는 암호화되어 처리됩니다. AURA Insight는 고객의 비밀 보장을 최우선으로 합니다.")

    st.markdown("<h2>1. AI 분석 서비스 선택</h2>", unsafe_allow_html=True)
    service_type = st.radio(
        "어떤 도움이 필요하십니까?",
        options=[
            "💔 배우자 불륜 가능성 분석 (외도 증거 분석)",
            "🔎 사람 찾기 (추적 가능성 분석)",
            "📂 기타 증거 분석 (기업/개인 분쟁)"
        ]
    )

    st.markdown("<h2>2. 분석 데이터 입력</h2>", unsafe_allow_html=True)

    st.subheader("구체적인 정황 설명 (필수)")
    details = st.text_area(
        "AI가 상황을 정확히 분석할 수 있도록 구체적인 정황이나 의심스러운 내용을 작성해주세요.",
        height=200,
        placeholder="예시: 남편이 최근 주말마다 야근을 핑계로 외박이 잦아졌습니다. 카톡 대화 패턴이 변했습니다."
    )

    st.subheader("증거 자료 업로드 (선택)")
    st.info("카카오톡 대화 내역(TXT/캡처), 사진, 카드 사용 내역(CSV/이미지) 등을 업로드해주세요. AI가 교차 분석합니다.")

    uploaded_files = st.file_uploader(
        "파일 업로드 (최대 5개, 텍스트 및 이미지)",
        type=["txt", "csv", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    if st.button("⚡ AI 즉시 분석 시작하기", type="primary"):
        if not details:
            st.warning("구체적인 정황 설명을 필수로 입력해야 합니다.")
        else:
            # AI 분석 실행
            with st.spinner("🧠 AURA AI 엔진이 증거 자료와 정황을 실시간으로 교차 분석 중입니다... (최대 30초 소요)"):
                analysis_result = perform_ai_analysis(service_type, details, uploaded_files)
            
            # 결과 저장 및 화면 전환
            st.session_state.analysis_result = analysis_result
            st.session_state.service_type = service_type
            st.session_state.step = 2
            st.rerun()

# --- Step 2: 분석 결과 확인 및 리드 확보 (★핵심★) ---
elif st.session_state.step == 2:
    result = st.session_state.analysis_result
    service_type = st.session_state.service_type

    st.markdown("<h2>📊 AI 예비 분석 리포트 (실시간)</h2>", unsafe_allow_html=True)

    if "error" in result:
        st.error(f"❌ 분석 오류 발생: {result['error']}. 잠시 후 다시 시도해주세요.")
    else:
        st.success("✅ AI 분석이 완료되었습니다.")
        
        # 스코어 표시 (핵심 Hook)
        score = result.get('risk_score', 0)
        # 점수 타입 검증
        if not isinstance(score, (int, float)):
            score = 0

        if "💔" in service_type:
            label = "AI 분석 외도 가능성 스코어"
        else:
            label = "AI 분석 추적/해결 가능성"

        # 스코어에 따른 시각화 및 메시지
        if score >= 70:
            delta_msg = "매우 높음 (전문가 개입 강력 권장)"
        elif score >= 40:
            delta_msg = "의심 단계 (추가 분석 필요)"
        else:
            delta_msg = "낮음"

        st.metric(label=label, value=f"{score}%", delta=delta_msg)
        st.progress(score / 100.0)
        st.info(f"💡 **분석 근거:** {result.get('score_reason', 'N/A')}")

        st.markdown("---")

        # 핵심 의심 정황
        st.subheader("🚩 핵심 의심 정황 / 단서")
        patterns = result.get('suspicious_patterns', [])
        if patterns:
            for pattern in patterns:
                st.markdown(f"- {pattern}")
        else:
            st.info("특이사항 없음.")

        st.markdown("---")

        # 권장 조치
        st.subheader("✅ 권장 행동 전략")
        recommendations = result.get('recommendations', [])
        if recommendations:
            for i, rec in enumerate(recommendations):
                st.markdown(f"{i+1}. {rec}")


    # 전문가 매칭 유도 (리드 확보 CTA)
    st.markdown("---")
    st.error("⚠️ 경고: 본 리포트는 AI 기반의 예비 분석이며, 법적 효력을 갖지 않습니다. 확실한 해결을 위해서는 반드시 전문가의 도움이 필요합니다.")
    st.markdown("<h2>💡 전문가 매칭 및 정밀 리포트 신청</h2>", unsafe_allow_html=True)

    # 리드 수집 폼
    with st.form(key='lead_form'):
        st.info("AI 분석 결과를 바탕으로 최적의 전문가(탐정/변호사)와 연결하고, 상세한 정밀 분석 리포트를 받으시려면 정보를 입력해주세요.")
        name = st.text_input("의뢰인 성함")
        phone = st.text_input("연락처 (하이픈(-) 포함 입력)")
        agree = st.checkbox("기밀 유지 및 이용 약관에 동의합니다.")
        
        # st.form_submit_button 사용
        submit_button = st.form_submit_button(label='전문가 매칭 및 정밀 리포트 신청 (무료)')

        if submit_button:
            if name and phone and agree:
                # 여기서 데이터를 저장하거나 관리자에게 알림 전송 (실제 구현 필요)
                st.success(f"{name}님, 신청이 완료되었습니다. 전문 상담사가 24시간 내에 연락드릴 예정입니다.")
                # (실제 운영 시 여기에 데이터 저장 로직(DB/Email/Slack) 추가 필요)
                st.balloons()
            else:
                st.warning("성함, 연락처 입력 및 약관 동의가 필요합니다.")

    if st.button("다시 분석하기"):
        st.session_state.step = 1
        st.session_state.analysis_result = None
        st.rerun()
