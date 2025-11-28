# app.py (IMD Insight v3.5 - OMEGA Protocol Integration)
import streamlit as st
import google.generativeai as genai
import time
import io
from PIL import Image
import json
import random
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------
st.set_page_config(
    page_title="아이엠디 인사이트 - 리스크 관리 매니저",
    page_icon="👁️",
    layout="centered"
)

# [Google API 및 시트 연동 설정]
try:
    # 1. Gemini API
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') 

    # 2. Google Sheets API (gcp_service_account 섹션 사용)
    SHEET_NAME = st.secrets["SHEET_NAME"] # secrets.toml에 SHEET_NAME = "IMD_DB" 등 설정 필요
    
    def init_google_sheet():
        # secrets에서 정보를 dict로 가져옴
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1

except Exception as e:
    st.error(f"❌ 시스템 초기화 실패: Secrets 설정을 확인하세요. {e}")
    st.stop()

# ---------------------------------------
# 1. UI/UX 스타일링 (Premium Dark + Cloaking)
# ---------------------------------------
custom_css = """
<style>
/* === 스트림릿 브랜딩 완전 제거 === */
#MainMenu { visibility: hidden !important; } 
header { visibility: hidden !important; }    
footer { visibility: hidden !important; }    
.stDeployButton { display: none !important; }
[data-testid="stSidebar"] { display: none; }

.stApp [data-testid="stDecoration"] { display: none !important; }
.stApp .main .block-container { padding-top: 2rem !important; }

/* === 모바일 최적화 === */
@media (max-width: 768px) {
    .stApp .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
}

/* === IMD Insight 프리미엄 다크 테마 === */
.stApp { background-color: #101010; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
h1 { color: #D4AF37; font-weight: 800; text-align: center; font-family: serif; }
h2, h3, h4 { color: #D4AF37; }

.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
    background-color: #2C2C2C; color: white; border: 1px solid #555;
}

/* 버튼 스타일링 */
.stButton>button[kind="primary"], div[data-testid="stForm"] button[type="submit"] {
    width: 100%; font-weight: bold; font-size: 18px !important; padding: 15px;
    background-color: #D4AF37 !important; color: #101010 !important; border-radius: 5px; border: none;
}
.stButton>button[kind="primary"]:hover, div[data-testid="stForm"] button[type="submit"]:hover {
    background-color: #B8860B !important;
}

/* OMEGA Protocol UI Elements */
.analysis-section {
    background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333;
}
/* 리스크 레벨 색상 */
.risk-critical { color: #FF4B4B !important; font-weight: bold; }
.risk-serious { color: #FFA500 !important; font-weight: bold; }
.risk-caution { color: #FFFF00 !important; font-weight: bold; }
.risk-normal { color: #00FF00 !important; font-weight: bold; }

/* GAP 강조 박스 */
.gap-highlight { border: 3px solid #FF4B4B; padding: 25px; background-color: #4a1a1a; margin-bottom: 20px; border-radius: 10px; }

/* 도파민 섹션 박스 */
.dopamine-box { border: 1px solid #D4AF37; padding: 15px; background-color: #222; border-radius: 8px; margin-bottom: 15px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. 로직 함수 (GitHub Data, AI Analysis)
# ---------------------------------------

# [GitHub 업체 리스트 가져오기]
@st.cache_data(ttl=600)
def fetch_agencies():
    # 지휘관의 GitHub 경로 (수정 금지)
    GITHUB_JSON_URL = "https://raw.githubusercontent.com/deokjune85-rgb/immiracle/main/agencies.json"
    try:
        response = requests.get(GITHUB_JSON_URL)
        if response.status_code == 200:
            return json.loads(response.text)
        return []
    except:
        return []

# [가중치 기반 랜덤 추천]
def get_weighted_recommendation(agencies):
    if not agencies: return None
    weights = [agency.get('weight', 10) for agency in agencies]
    try:
        selected = random.choices(agencies, weights=weights, k=1)[0]
        return selected
    except:
        return agencies[0] # 에러 시 첫 번째(보통 본사) 리턴

# [AI 프롬프트 생성]
def get_analysis_prompt(service_type):
    # OMEGA Protocol JSON Schema (도파민 섹션 추가됨)
    omega_schema = """
    {
      "risk_assessment": {
        "score": (int: 0-100),
        "level": "(string: CRITICAL, SERIOUS, CAUTION, NORMAL)",
        "summary": "(string: 1-2 문장 요약)"
      },
      "deep_analysis": {
        "linguistic": { "keywords": ["(string)"], "analysis": "(string)" },
        "alibi_mismatch": { "discrepancies": ["(string)"], "analysis": "(string)" },
        "behavioral": { "indicators": ["(string)"], "analysis": "(string)" }
      },
      "litigation_readiness": {
        "suspicion_score": (int),
        "evidence_score": (int: 매우 엄격하게 평가, 30 이하 권장),
        "warning": "(string)",
        "needed_evidence": ["(string)"]
      },
      "golden_time": {
        "cctv_expiry_days": (int),
        "blackbox_expiry_days": (int),
        "urgency_message": "(string)"
      },
      "villain_profiling": {
        "type": "(string: 예: 용의주도한 소시오패스형, 회피형 겁쟁이 등)",
        "traits": "(string: 성격 특성)",
        "weakness": "(string: 약점)",
        "counter_strategy": "(string: 공략법)"
      },
      "financial_forecast": {
        "total_amount": "(string: 예: 약 3억 5천만 원)",
        "breakdown": "(string: 예: 재산분할 3억 + 위자료 3천 + 양육비)",
        "comment": "(string: 돈으로 환산했을 때의 멘트)"
      },
      "simulation": {
        "question": "(string: 예: 지금 당장 추궁한다면?)",
        "bad_choice_result": "(string: 망하는 시나리오)",
        "good_choice_result": "(string: 전문가와 함께 증거 잡는 시나리오)"
      }
    }
    """

    if "💔" in service_type:
        return f"""
        [시스템 역할]: 냉철한 AI 탐정 및 법률 전략가.
        [목표]: 정황과 증거를 분석하여 외도 가능성을 진단하고, 사용자에게 '전문가(탐정/변호사)'의 필요성을 각인시킬 것.
        [지침]:
        1. 'evidence_score'는 낮게 책정하여 증거 부족을 강조할 것.
        2. 'villain_profiling'은 MBTI나 심리학적 용어를 섞어 흥미롭게 작성할 것.
        3. 'financial_forecast'는 구체적인 금액을 제시하여 동기를 부여할 것.
        
        [입력 데이터 기반 분석 수행]
        [출력 형식]: JSON Only
        {omega_schema}
        """
    else:
        return None

def perform_ai_analysis(service_type, details, uploaded_files):
    prompt = get_analysis_prompt(service_type)
    if not prompt: return {"error": "서비스 준비 중"}

    input_payload = [prompt, f"\n[정황 설명]\n{details}\n"]

    if uploaded_files:
        input_payload.append("\n[증거 파일]\n")
        for file in uploaded_files:
            try:
                if file.type.startswith("image/"):
                    img = Image.open(file)
                    input_payload.append(img)
                elif "text" in file.type or "csv" in file.type:
                    text_data = file.getvalue().decode("utf-8", errors='ignore')
                    input_payload.append(f"파일명: {file.name}\n{text_data[:3000]}")
            except: pass

    try:
        config = genai.GenerationConfig(temperature=0.3, response_mime_type="application/json")
        response = model.generate_content(input_payload, generation_config=config)
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"분석 실패: {e}"}

# ---------------------------------------
# 3. 메인 애플리케이션 (Frontend)
# ---------------------------------------

st.title("아이엠디 인사이트 - 리스크 관리 매니지먼트")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>AI 기반 진실 분석 및 전문가 매칭 플랫폼</h3>", unsafe_allow_html=True)
st.markdown("---")

if 'step' not in st.session_state: st.session_state.step = 1

# === Step 1: 입력 ===
if st.session_state.step == 1:
    st.warning("🔒 모든 데이터는 암호화 처리 후 즉시 파기됩니다.")
    
    st.markdown("<h2>1. 분석 서비스 선택</h2>", unsafe_allow_html=True)
    service_type = st.radio("분석 유형", ["💔 배우자 외도/불륜 정밀 분석", "🔎 (준비중) 사람 찾기/추적 분석"])

    st.markdown("<h2>2. 데이터 입력</h2>", unsafe_allow_html=True)
    details = st.text_area("구체적인 정황 설명 (필수)", height=200, placeholder="예: 남편의 귀가가 늦고, 핸드폰 패턴이 바뀌었습니다.")
    
    uploaded_files = st.file_uploader("증거 자료 (선택: 카톡, 사진, 녹취 등)", accept_multiple_files=True)

    if st.button("⚡ AI 포렌식 분석 시작", type="primary"):
        if not details:
            st.warning("정황 설명을 입력해주세요.")
        else:
            with st.spinner("증거 데이터 교차 검증 및 법적 효력 분석 중..."):
                result = perform_ai_analysis(service_type, details, uploaded_files)
                st.session_state.analysis_result = result
                st.session_state.service_type = service_type
                
                # 업체 추천 로직 (가중치 기반) - 분석 시점에 미리 뽑아둠
                agencies = fetch_agencies()
                st.session_state.recommended_agency = get_weighted_recommendation(agencies)
                
                st.session_state.step = 2
                st.rerun()

# === Step 2: 결과 리포트 ===
elif st.session_state.step == 2:
    result = st.session_state.analysis_result
    
    if "error" in result:
        st.error(result['error'])
        if st.button("돌아가기"): 
            st.session_state.step = 1
            st.rerun()
    else:
        # 1. 스코어
        risk = result.get('risk_assessment', {})
        level_cls = get_risk_style(risk.get('level', 'NORMAL'))
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("📊 AI 진단 결과")
        st.markdown(f"### 위험도: <span class='{level_cls}'>{risk.get('level')} ({risk.get('score')}%)</span>", unsafe_allow_html=True)
        st.info(risk.get('summary'))
        st.markdown('</div>', unsafe_allow_html=True)

        # 2. 도파민 섹션 (빌런 프로파일링)
        villain = result.get('villain_profiling', {})
        if villain:
            st.markdown('<div class="dopamine-box">', unsafe_allow_html=True)
            st.markdown(f"### 🃏 상대방 프로파일링: [{villain.get('type')}]")
            st.write(f"**특징:** {villain.get('traits')}")
            st.write(f"**약점:** {villain.get('weakness')}")
            st.success(f"**⚔️ 공략법:** {villain.get('counter_strategy')}")
            st.markdown('</div>', unsafe_allow_html=True)

        # 3. 법적 효력 (GAP)
        readiness = result.get('litigation_readiness', {})
        st.markdown('<div class="gap-highlight">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        col1.metric("심증 (의심)", f"{readiness.get('suspicion_score')}%")
        col2.metric("물증 (법적효력)", f"{readiness.get('evidence_score')}%", delta="-부족", delta_color="inverse")
        st.error(f"⚠️ {readiness.get('warning')}")
        st.markdown("**[필요한 핵심 증거]**")
        for req in readiness.get('needed_evidence', []):
            st.markdown(f"- {req}")
        st.markdown('</div>', unsafe_allow_html=True)

        # 4. 금융 치료 계산기
        money = result.get('financial_forecast', {})
        if money:
            st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
            st.subheader("💰 예상 금융 치료 견적")
            st.markdown(f"## 💵 Total: {money.get('total_amount')}")
            st.text(f"내역: {money.get('breakdown')}")
            st.caption(money.get('comment'))
            st.markdown('</div>', unsafe_allow_html=True)

        # 5. 골든 타임
        golden = result.get('golden_time', {})
        st.warning(f"⏳ **골든 타임 경고:** CCTV 보존 기한이 약 {golden.get('cctv_expiry_days')}일 남았습니다. {golden.get('urgency_message')}")

        # 6. 전문가 매칭 (가중치 적용)
        st.markdown("---")
        target_agency = st.session_state.get('recommended_agency')
        
        st.markdown("<h2>💡 AI 추천 해결사 (Premium Partner)</h2>", unsafe_allow_html=True)
        st.info("귀하의 사건 유형과 난이도를 분석하여, 해결 확률이 가장 높고 검증된 곳을 연결합니다.")

        if target_agency:
            with st.container(border=True):
                st.markdown(f"### 🏆 {target_agency.get('name', 'IMD 인증 본부')}")
                st.write(f"**특징:** {target_agency.get('desc', '디지털 포렌식 및 심층 조사 전문')}")
                st.write(f"**연락처:** **{target_agency.get('phone', '010-0000-0000')}**")
                st.link_button("📞 전문가와 바로 상담하기 (비공개)", target_agency.get('url', '#'))
        
        # 7. DB 수집 폼
        with st.form("lead_form"):
            st.write("🔒 **상세 리포트 및 전문가 히든 전략 무료 받기**")
            c_name = st.text_input("성함 (익명 가능)")
            c_phone = st.text_input("연락처 (결과 전송용)")
            c_agree = st.checkbox("개인정보 처리방침 동의")
            
            if st.form_submit_button("전략 리포트 받기"):
                if c_name and c_phone and c_agree:
                    try:
                        sheet = init_google_sheet()
                        # 날짜, 이름, 전화번호, 서비스유형, 추천업체
                        row = [
                            str(datetime.now()), 
                            c_name, 
                            c_phone, 
                            st.session_state.service_type, 
                            target_agency.get('name') if target_agency else "N/A"
                        ]
                        sheet.append_row(row)
                        st.success("✅ 신청 완료! 담당자가 분석된 전략을 가지고 곧 연락드립니다.")
                    except Exception as e:
                        st.error(f"전송 실패: {e}")
                else:
                    st.warning("정보를 입력해주세요.")

    if st.button("처음으로"):
        st.session_state.step = 1
        st.rerun()
