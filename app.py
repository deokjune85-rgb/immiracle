# app.py (IMD Insight v3.0 - OMEGA Protocol Implementation)
import streamlit as st
import google.generativeai as genai
import time
import io
from PIL import Image
import json
import random

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------
st.set_page_config(
    page_title="아이엠디 인사이트 - 리스크 관리 매니저",
    page_icon="👁️",
    layout="centered"
)

# API 키 설정 (Streamlit Secrets 사용)
try:
    # 보안을 위해 API 키는 Streamlit Secrets에서 로드해야 합니다.
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 멀티모달 분석 및 JSON 모드 지원 모델
    model = genai.GenerativeModel('gemini-2.0-flash') 
except Exception as e:
    st.error(f"❌ AI 엔진 초기화 실패: GOOGLE_API_KEY를 Streamlit Secrets에 설정하세요. {e}")
    st.stop()

# ---------------------------------------
# 1. UI/UX 스타일링 (Premium Dark + Cloaking + OMEGA Protocol)
# ---------------------------------------
custom_css = """
<style>
/* === 스트림릿 브랜딩 완전 제거 (스텔스 모드) === */
#MainMenu { visibility: hidden !important; } 
header { visibility: hidden !important; }    
footer { visibility: hidden !important; }    
.stDeployButton { display: none !important; }
[data-testid="stSidebar"] { display: none; } /* 사이드바 제거 */

/* 상단 장식 제거 및 패딩 조정 */
.stApp [data-testid="stDecoration"] {
    display: none !important;
}
.stApp .main .block-container {
    padding-top: 2rem !important; 
}

/* === 모바일 최적화 === */
@media (max-width: 768px) {
    .stApp .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}

/* === IMD Insight 프리미엄 다크 테마 === */
.stApp {
    background-color: #101010; /* Deep Black */
    color: #E0E0E0;
    font-family: 'Pretendard', sans-serif;
}
h1 {
    color: #D4AF37; /* Premium Gold */
    font-weight: 800;
    text-align: center;
    font-family: serif;
}
h2, h3, h4 { color: #D4AF37; }

.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
    background-color: #2C2C2C;
    color: white;
    border: 1px solid #555;
}
/* 버튼 스타일링 */
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

/* OMEGA Protocol UI Elements */
.analysis-section {
    background-color: #1E1E1E;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border: 1px solid #333;
}
/* 리스크 레벨 색상 정의 */
.risk-critical { color: #FF4B4B !important; font-weight: bold; }
.risk-serious { color: #FFA500 !important; font-weight: bold; }
.risk-caution { color: #FFFF00 !important; font-weight: bold; }
.risk-normal { color: #00FF00 !important; font-weight: bold; }

/* GAP 강조 박스 */
.gap-highlight { border: 3px solid #FF4B4B; padding: 25px; background-color: #4a1a1a; margin-bottom: 20px; border-radius: 10px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. AI 분석 엔진 (OMEGA Protocol JSON Schema)
# ---------------------------------------

def get_analysis_prompt(service_type):
    """서비스 유형에 따른 AI 분석 프롬프트 정의 (OMEGA Protocol JSON 출력 강제)."""
    
    # OMEGA Protocol JSON Schema 정의 (v3.0)
    omega_schema = """
    {
      "risk_assessment": {
        "score": (int: 0-100, 외도 가능성 점수),
        "level": "(string: CRITICAL, SERIOUS, CAUTION, NORMAL 중 하나)",
        "summary": "(string: 1-2 문장의 충격적인 상황 요약 및 행동 촉구 메시지)"
      },
      "deep_analysis": {
        "linguistic": {
          "keywords": ["(string: 의심 키워드 1)", "(string: 키워드 2)"],
          "analysis": "(string: 언어 패턴, 톤, 빈도 분석. 텍스트 증거 없을 시 'N/A')"
        },
        "alibi_mismatch": {
          "discrepancies": ["(string: 발견된 구체적인 모순점 또는 거짓말)"],
          "analysis": "(string: 알리바이 모순에 대한 결론. 관련 데이터 없을 시 'N/A')"
        },
        "behavioral": {
          "indicators": ["(string: 의심 행동 1)", "(string: 행동 2)"],
          "analysis": "(string: 묘사된 행동이나 사진 증거 기반의 심리 해석)"
        }
      },
      "litigation_readiness": {
        "suspicion_score": (int: 심증 강도, risk_assessment.score와 동일),
        "evidence_score": (int: 현재 증거의 법적 효력 점수. 0-100. 매우 엄격하고 보수적으로 평가. 결정적 증거 없으면 30점 이하.),
        "warning": "(string: 현재 증거가 법적으로 불충분한 이유 강조. 패소 위험 경고.)",
        "needed_evidence": ["(string: 예: 숙박업소 출입 영상)", "(string: 예: 직접적인 애정표현 녹취)"]
      },
      "golden_time": {
        "cctv_expiry_days": (int: CCTV 예상 보존 기한 일수, 보통 7-14일 랜덤),
        "blackbox_expiry_days": (int: 블랙박스 예상 덮어쓰기 기한 일수, 보통 2-5일 랜덤),
        "urgency_message": "(string: 증거 소멸 위험을 강조하는 긴급 경고 메시지)"
      }
    }
    """

    if "💔" in service_type: # 불륜 분석
        return f"""
        [시스템 역할]: 법의학 수준의 AI 포렌식 분석가. 감정 배제, 객관적 데이터 기반 분석.
        [목표]: 제공된 정황 설명과 증거 파일(텍스트, 이미지 등)을 교차 분석하여 '불륜 가능성'을 평가하고 법적 준비도를 진단.
        [분석 지침]:
        1. 모든 입력 데이터를 철저히 분석 (텍스트 내용, 이미지 속성, 파일 종류 등).
        2. OMEGA Protocol 지침에 따라 각 항목을 계산하고 분석 결과를 도출.
        3. 특히 'litigation_readiness.evidence_score'는 매우 엄격하게 평가하여 전문가의 필요성을 강조. 결정적 증거(성관계 증명 등) 없으면 점수를 낮게 부여.
        
        [입력 데이터]
        정황 설명 및 증거 파일 내용이 멀티모달 입력으로 제공됩니다.

        [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력. 다른 설명은 절대 금지.
        {omega_schema}
        """
    # (사람 찾기 등 다른 서비스 유형도 유사한 구조로 추가 가능)
    else:
        return None 

def perform_ai_analysis(service_type, details, uploaded_files):
    """멀티모달 AI 분석을 실행하고 OMEGA JSON 결과를 파싱합니다."""
    
    prompt = get_analysis_prompt(service_type)
    if not prompt:
        return {"error": "현재 해당 서비스는 준비 중입니다. (불륜 가능성 분석만 지원)"}

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
                    img.convert('RGB').save(img_byte_arr, format='JPEG', quality=85)
                    input_payload.append({"mime_type": "image/jpeg", "data": img_byte_arr.getvalue()})
                
                elif file.type == "text/plain" or "csv" in file.type:
                    try:
                        string_data = file.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                           string_data = file.getvalue().decode("cp949")
                        except:
                            string_data = "[파일 디코딩 실패]"
                    input_payload.append(f"--- 파일명: {file.name} (텍스트) ---\n{string_data[:5000]}\n")

            except Exception as e:
                print(f"File processing error: {e}")

    # 3. AI API 호출 (JSON 모드 강제)
    try:
        # Temperature 0.2로 설정하여 객관성 및 일관성 극대화, JSON 출력 강제
        generation_config = genai.GenerationConfig(temperature=0.2, response_mime_type="application/json")
        safety_settings = [{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
        
        response = model.generate_content(input_payload, generation_config=generation_config, safety_settings=safety_settings)
        
        # JSON 응답 파싱
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {"error": f"AI 분석 중 오류 발생 또는 응답 형식 오류: {e}."}

# ---------------------------------------
# 3. 헬퍼 함수 (UI 지원)
# ---------------------------------------
def get_risk_style(level):
    if level == "CRITICAL": return "risk-critical"
    if level == "SERIOUS": return "risk-serious"
    if level == "CAUTION": return "risk-caution"
    return "risk-normal"

# ---------------------------------------
# 4. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

st.title("아이엠디 인사이트 - 리스크 관리 매니지먼트")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>AI 기반 진실 분석 및 전문가 매칭 플랫폼</h3>", unsafe_allow_html=True)
st.markdown("---")

# 세션 상태 관리
if 'step' not in st.session_state:
    st.session_state.step = 1

# --- Step 1: 서비스 선택 및 데이터 입력 ---
if st.session_state.step == 1:
    st.warning("🔒 모든 데이터는 암호화되어 처리됩니다. 아이엠디 인사이트는 고객의 비밀 보장을 최우선으로 합니다.")

    st.markdown("<h2>1. AI 분석 서비스 선택</h2>", unsafe_allow_html=True)
    service_type = st.radio(
        "어떤 도움이 필요하십니까?",
        options=[
            "💔 배우자 불륜 가능성 분석 (외도 증거 분석)",
            # "🔎 사람 찾기 (추적 가능성 분석) - 준비 중",
        ]
    )

    st.markdown("<h2>2. 분석 데이터 입력</h2>", unsafe_allow_html=True)

    st.subheader("구체적인 정황 설명 (필수)")
    details = st.text_area(
        "AI가 상황을 정확히 분석할 수 있도록 구체적인 정황이나 의심스러운 내용을 작성해주세요.",
        height=200,
        placeholder="예시: 남편이 최근 주말마다 야근을 핑계로 외박이 잦아졌습니다. 카톡 대화 패턴이 변했고, 차량 이동 경로가 의심스럽습니다."
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
            with st.spinner("아이엠디 AI 엔진이 증거 자료와 정황을 실시간으로 교차 분석 중입니다... (최대 30초 소요)"):
                analysis_result = perform_ai_analysis(service_type, details, uploaded_files)
            
            # 결과 저장 및 화면 전환
            st.session_state.analysis_result = analysis_result
            st.session_state.service_type = service_type
            st.session_state.step = 2
            st.rerun()

# --- Step 2: 분석 결과 확인 (OMEGA Protocol UI) ---
elif st.session_state.step == 2:
    result = st.session_state.analysis_result
    service_type = st.session_state.service_type

    st.markdown("<h2>아이엠디 인사이트 - 최종 분석 리포트</h2>", unsafe_allow_html=True)

    if "error" in result:
        st.error(f"❌ 분석 오류 발생: {result['error']}. 잠시 후 다시 시도해주세요.")
    
    # OMEGA 프로토콜 적용된 서비스 (불륜 분석)
    elif "💔" in service_type:
        
        # === SECTION 1: 헤더 & 스코어 (시각적 압도) ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("AI 정밀 진단 결과")
        
        risk = result.get('risk_assessment', {})
        score = risk.get('score', 0)
        level = risk.get('level', 'NORMAL')
        summary = risk.get('summary', 'N/A')
        level_class = get_risk_style(level)

        st.markdown(f"### 외도 위험도 (Risk Level)")
        # 시각적 임팩트를 위해 h1 태그 사용
        st.markdown(f"<h1 class='{level_class}'>{level} ({score}%)</h1>", unsafe_allow_html=True)
        st.error(f"💬 **AI 코멘트:** {summary}")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === SECTION 2: 상세 분석 (Deep Analysis) ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("🧐 AI 증거 해부 (Deep Analysis)")
        
        analysis = result.get('deep_analysis', {})
        
        # 1. 언어 패턴 분석
        st.markdown("#### 1. 언어 패턴 분석 (Linguistic Pattern)")
        ling = analysis.get('linguistic', {})
        st.text(f"감지된 키워드: {', '.join(ling.get('keywords', []))}")
        st.write(f"분석: {ling.get('analysis', 'N/A')}")
        st.markdown("---")

        # 2. 알리바이 모순
        st.markdown("#### 2. 알리바이 모순 (Alibi Mismatch)")
        alibi = analysis.get('alibi_mismatch', {})
        st.text(f"모순점: {', '.join(alibi.get('discrepancies', []))}")
        st.write(f"결론: {alibi.get('analysis', 'N/A')}")
        st.markdown("---")

        # 3. 행동 심리 분석
        st.markdown("#### 3. 행동 심리 분석 (Behavioral)")
        behav = analysis.get('behavioral', {})
        st.text(f"징후: {', '.join(behav.get('indicators', []))}")
        st.write(f"해석: {behav.get('analysis', 'N/A')}")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === SECTION 3: 법적 효력 진단 (The Gap - ★핵심★) ===
        st.markdown('<div class="gap-highlight">', unsafe_allow_html=True)
        st.subheader("⚖️ 법적 소송 준비도 (Litigation Readiness)")

        readiness = result.get('litigation_readiness', {})
        suspicion = readiness.get('suspicion_score', score) # 없을 경우 risk_score 사용
        evidence = readiness.get('evidence_score', 0)

        col1, col2 = st.columns(2)
        col1.metric(label="심증 (의심 강도)", value=f"{suspicion}%", delta="높음")
        # 물증 점수는 낮음을 강조하기 위해 delta_color="inverse" 사용
        col2.metric(label="물증 (법적 효력)", value=f"{evidence}%", delta="매우 부족", delta_color="inverse")

        st.error(f"⚠️ **경고:** {readiness.get('warning', 'N/A')}")
        st.markdown(f"🚨 **필요한 결정적 물증 (Critical Evidence):**")
        for item in readiness.get('needed_evidence', []):
            st.markdown(f"- **{item}**")

        st.markdown('</div>', unsafe_allow_html=True)

        # === SECTION 4: 긴급 행동 지침 (Urgency) ===
        # 배경색을 어둡게 하여 긴급성 강조
        st.markdown('<div class="analysis-section" style="background-color: #332900;">', unsafe_allow_html=True) 
        st.subheader("⏳ 골든 타임 경고 (Golden Time)")

        golden = result.get('golden_time', {})
        # AI가 생성하지 못했을 경우를 대비해 안전하게 처리
        cctv = golden.get('cctv_expiry_days', 'N/A')
        blackbox = golden.get('blackbox_expiry_days', 'N/A')

        st.markdown(f"**CCTV 보존 기한:** 약 **{cctv}일** 남음")
        st.markdown(f"**차량 블랙박스 덮어쓰기:** 약 **{blackbox}일** 남음")
        st.warning(f"🚨 **긴급 메시지:** {golden.get('urgency_message', '증거가 곧 소멸될 수 있습니다.')}")

        st.markdown('</div>', unsafe_allow_html=True)


    # === SECTION 5: 전문가 매칭 CTA (해결책 제시) ===
    st.markdown("---")
    st.markdown("<h2>💡 아이엠디 솔루션 : 전문가 연결</h2>", unsafe_allow_html=True)
    st.info("AI가 귀하의 케이스에 가장 적합한 [지역 전문 탐정]과 [이혼 전문 변호사]를 선별했습니다. 사라지기 전에 증거를 잡고, 법대로 응징하십시오.")

    # 리드 수집 폼
    with st.form(key='lead_form'):
        st.markdown("#### 비공개 무료 견적 받기")
        name = st.text_input("의뢰인 성함 (익명 가능)")
        phone = st.text_input("연락처 (안심 번호 가능)")
        agree = st.checkbox("기밀 유지 및 전문가 매칭에 동의합니다.")
        
        submit_button = st.form_submit_button(label='전문가 리스트 확인 및 상담 신청')

        if submit_button:
            if name and phone and agree:
                # 여기서 데이터를 저장하거나 관리자에게 알림 전송 (실제 구현 필요)
                st.success(f"{name}님, 신청이 완료되었습니다. 전문 상담사가 즉시 배정되어 연락드릴 예정입니다. (데모 버전)")
                st.balloons()
            else:
                st.warning("정보 입력 및 약관 동의가 필요합니다.")

    if st.button("다시 분석하기"):
        st.session_state.step = 1
        st.session_state.analysis_result = None
        st.rerun()
