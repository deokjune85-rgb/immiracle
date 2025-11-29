# app.py (IMD Insight v5.0 - Questionnaire & Multi-Recommendation Engine)
import streamlit as st
import google.generativeai as genai
import time
import json
import random
import hashlib
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------

# [★중요★] 여기에 깃허브 JSON 파일의 Raw URL을 입력하세요.
GITHUB_JSON_URL = "https://raw.githubusercontent.com/deokjune85-rgb/immiracle/refs/heads/main/agencies.json" 

st.set_page_config(
    page_title="IMD Insight - AI 기반 진실 분석 및 법률 전략실",
    layout="centered"
)

# API 키 설정 (Gemini)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 분석용 모델(정확성)과 생성용 모델(창의성)을 동일 인스턴스로 사용하되, 호출 시 설정을 변경
    model = genai.GenerativeModel('gemini-1.5-flash-latest') 
except Exception:
    model = None # API 키 오류 시에도 시스템 작동 유지

# ---------------------------------------
# 1. UI/UX 스타일링 (IMD Branding + Cloaking)
# ---------------------------------------
custom_css = """
<style>
/* === 스트림릿 브랜딩 완전 제거 (스텔스 모드) === */
#MainMenu { visibility: hidden !important; } 
header { visibility: hidden !important; }    
footer { visibility: hidden !important; }    
.stDeployButton { display: none !important; }
[data-testid="stSidebar"] { display: none; } 

/* 상단 장식 제거 및 패딩 조정 */
.stApp [data-testid="stDecoration"] { display: none !important; }
.stApp .main .block-container { padding-top: 2rem !important; }

/* === IMD Insight 프리미엄 다크 테마 === */
.stApp {
    background-color: #0C0C0C;
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

.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div, .stRadio > div {
    background-color: #2C2C2C;
    color: white;
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

/* GAP 강조 박스 */
.gap-highlight { border: 3px solid #FF4B4B; padding: 25px; background-color: #4a1a1a; margin-bottom: 20px; border-radius: 10px; }

/* THE VAULT 스타일 */
.vault-confirmation { background-color: #2a2a4a; color: #00FF00; padding: 15px; border-radius: 5px; font-family: monospace; margin-bottom: 20px; }

/* 파트너사 추천 박스 스타일 */
.partner-box {
    background-color: #2C2C2C;
    border: 1px solid #555;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.partner-name {
    font-size: 18px;
    font-weight: bold;
    color: #D4AF37;
    margin-bottom: 5px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. 데이터 로딩 및 처리 (JSON 가중치 시스템)
# ---------------------------------------

@st.cache_data(ttl=600)
def fetch_agencies():
    """깃허브에서 파트너사 JSON 데이터를 가져옵니다."""
    if GITHUB_JSON_URL.endswith("YOUR_ID/YOUR_REPO/main/agencies.json"):
        return []
    try:
        response = requests.get(GITHUB_JSON_URL)
        if response.status_code == 200:
            data = json.loads(response.text)
            for item in data:
                if not isinstance(item.get('weight'), (int, float)) or item.get('weight', 0) <= 0:
                    item['weight'] = 1
            return data
        return []
    except Exception as e:
        print(f"Error fetching agencies: {e}")
        return []

def get_weighted_unique_recommendations(agencies, k=3):
    """가중치를 기반으로 고유한 파트너사 K개를 선택합니다. (★v5.0 핵심 로직★)"""
    if not agencies or k <= 0:
        return []

    # 사용 가능한 업체 수가 요청 수(K)보다 적으면 모두 반환 (랜덤 셔플)
    if len(agencies) <= k:
        shuffled = list(agencies)
        random.shuffle(shuffled)
        return shuffled

    selected = []
    # 중복을 피하기 위해 복사본 생성
    pool = list(agencies)
    
    # 가중치 기반 선택 (중복 없이 k개 선택)
    for _ in range(k):
        if not pool:
            break
            
        weights = [agency.get('weight', 1) for agency in pool]
        
        try:
            # 가중치 기반으로 1개 선택
            choice = random.choices(pool, weights=weights, k=1)[0]
            selected.append(choice)
            # 선택된 항목 제거하여 중복 방지
            pool.remove(choice)
        except Exception as e:
            # 오류 발생 시 남은 항목에서 랜덤 선택 (Fallback)
            print(f"Weighted selection error: {e}. Falling back.")
            choice = random.choice(pool)
            selected.append(choice)
            pool.remove(choice)

    return selected

# 파트너사 데이터 로드 실행
PARTNER_AGENCIES = fetch_agencies()

# ---------------------------------------
# 3. 리드 캡처 시스템 (Google Sheets 연동)
# ---------------------------------------
def save_lead_to_google_sheets(lead_data):
    """고객 리드 정보를 Google Sheets에 저장합니다."""
    try:
        creds_dict = st.secrets["gcp_service_account"].to_dict()
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        sheet_name = st.secrets.get("SHEET_NAME", "IMD_Insight_Leads_DB")
        sheet = client.open(sheet_name).sheet1

        if not sheet.row_values(1):
            # 헤더 수정: Details 대신 Questionnaire Data, Vault Hash 추가
            headers = ["Timestamp", "Name", "Phone", "Risk Score", "Evidence Score", "Service Type", "Questionnaire Data", "Vault Hash", "Recommended Partners"]
            sheet.append_row(headers)

        values = [
            lead_data.get("timestamp"),
            lead_data.get("name"),
            lead_data.get("phone"),
            lead_data.get("risk_score"),
            lead_data.get("evidence_score"),
            lead_data.get("service_type"),
            json.dumps(lead_data.get("questionnaire_data", {}), ensure_ascii=False),
            lead_data.get("vault_hash"),
            lead_data.get("recommended_partners")
        ]
        sheet.append_row(values)
        return True
    except Exception as e:
        print(f"Google Sheets 연동 실패: {e}")
        return False 

# ---------------------------------------
# 4. AI 분석 엔진 (OMEGA Protocol - 설문 기반)
# ---------------------------------------

def get_analysis_prompt(service_type, dossier_info, questionnaire_data):
    """설문 기반 AI 분석 프롬프트 정의 (v5.0 Schema)."""
    
    # OMEGA Protocol JSON Schema (v5.0 수정)
    omega_schema = """
    {
      "risk_assessment": {
        "score": (int: 0-100),
        "level": "(string: CRITICAL, SERIOUS, CAUTION, NORMAL)",
        "summary": "(string: 충격적인 상황 요약 및 행동 촉구 메시지)"
      },
      "deep_analysis": {
        "communication": {
          "analysis": "(string: 연락/대화 패턴 분석)"
        },
        "behavioral": {
          "analysis": "(string: 행동 변화 및 의심 정황 분석)"
        },
        "financial": {
           "analysis": "(string: 재정 활동 분석 - 관련 설문 기반)"
        }
      },
      "litigation_readiness": {
        "suspicion_score": (int),
        "evidence_score": (int: 법적 효력 점수. 설문 기반이므로 매우 낮게 평가(0-20점).),
        "warning": "(string: 설문만으로는 증거 불충분함을 강력히 경고. 물리적 증거 필요성 강조.)",
        "needed_evidence": ["(string)"]
      },
      "golden_time": {
        "urgency_message": "(string: 증거 소멸 위험 강조 메시지)"
      },
      "the_dossier": {
        "profile": "(string: 상대방 프로파일링 및 약점 분석)",
        "negotiation_strategy": "(string: 협상/소송 전략 제안)"
      },
      "the_war_room": {
        "step1_title": "(string)",
        "step1_action": "(string)",
        "step2_title": "(string)",
        "step2_action": "(string)",
        "step3_title": "(string)",
        "step3_action": "(string)"
      }
    }
    """

    # 설문 데이터를 텍스트로 변환
    q_data_text = "\n".join([f"- {q}: {a}" for q, a in questionnaire_data.items()])

    if "💔" in service_type: # 불륜 분석
        return f"""
        [시스템 역할]: AI 기반 외도 위험성 평가 전략가.
        [목표]: 입력된 설문 데이터와 상대방 정보를 기반으로 '불륜 가능성'을 평가하고 전략 로드맵(War Room) 및 대상자 프로파일링(Dossier)을 제시.
        [분석 지침]:
        1. 입력된 설문조사 결과를 객관적인 데이터로 간주하고 분석. 응답의 강도('매우 그렇다' 등)를 반영할 것.
        2. 상대방 정보(직업/성향)를 고려하여 'the_dossier'와 'the_war_room'을 맞춤 설계.
        3. ★중요★ 'litigation_readiness.evidence_score'는 극도로 낮게 평가해야 함 (설문은 심증일 뿐 물증이 아님). 물리적 증거 확보의 필요성을 강력히 경고할 것.
        
        [입력 데이터 요약]
        1. 상대방 직업/성향 (THE DOSSIER 정보): {dossier_info}
        2. [설문조사 결과 (증거 데이터)]:
        {q_data_text}

        [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력. 다른 설명은 절대 금지.
        {omega_schema}
        """
    else:
        return None 

def perform_ai_analysis(service_type, dossier_info, questionnaire_data):
    """AI 분석을 실행하고 OMEGA JSON 결과를 파싱합니다."""
    if not model:
        return {"error": "AI 엔진이 초기화되지 않았습니다. (API 키 확인 필요)"}

    prompt = get_analysis_prompt(service_type, dossier_info, questionnaire_data)
    if not prompt:
        return {"error": "현재 해당 서비스는 준비 중입니다."}

    # AI API 호출 (JSON 모드 강제)
    try:
        # Temperature 0.2로 설정하여 객관성 확보
        generation_config = genai.GenerationConfig(temperature=0.2, response_mime_type="application/json")
        safety_settings = [{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
        
        # 설문 기반이므로 입력은 텍스트 프롬프트만 사용
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {"error": f"AI 분석 중 오류 발생 또는 응답 형식 오류: {e}."}

# ---------------------------------------
# 5. AI 추천 이유 생성기 (★v5.0 신규★)
# ---------------------------------------
def generate_recommendation_reasons(agencies, analysis_result):
    """AI를 사용하여 분석 결과에 기반한 맞춤형 추천 이유를 생성합니다. (JSON 모드)"""
    
    if not model or not agencies:
        return {}

    # 파트너 정보 포맷팅 및 예상 JSON 구조 생성
    agency_list_text = ""
    expected_json_structure = "{\n"
    for agency in agencies:
        agency_list_text += f"- 업체명: {agency['name']}\n  특징: {agency['desc']}\n"
        expected_json_structure += f'  "{agency["name"]}": "(string: 추천 이유)",\n'
    expected_json_structure = expected_json_structure.rstrip(',\n') + "\n}"

    # 분석 결과 요약
    risk_summary = analysis_result.get('risk_assessment', {}).get('summary', 'N/A')
    needed_evidence = ", ".join(analysis_result.get('litigation_readiness', {}).get('needed_evidence', []))

    prompt = f"""
    당신은 IMD Insight의 수석 컨설턴트입니다. AI 분석 결과를 바탕으로, 추천된 전문 업체(탐정사무소)들이 왜 이 의뢰인에게 적합한지 설명하는 '추천 이유'를 생성해야 합니다.

    [AI 분석 요약]
    - 리스크 요약: {risk_summary}
    - 필요한 증거: {needed_evidence}

    [추천 대상 업체 목록]
    {agency_list_text}

    [작성 지침]:
    1. 각 업체별로 추천 이유를 1~2문장으로 작성합니다.
    2. 업체의 '특징'과 의뢰인의 '현재 상황(분석 결과)'을 연결하여 설득력 있게 작성합니다.
    3. 창의적이고 전문적인 어조를 사용합니다. (환각 허용)

    [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력. Key는 업체명, Value는 추천 이유입니다.
    {expected_json_structure}
    """
    try:
        # 창의성을 위해 Temperature 0.7 사용, JSON 모드 강제
        generation_config = genai.GenerationConfig(temperature=0.7, response_mime_type="application/json")
        response = model.generate_content(prompt, generation_config=generation_config)
        reasons = json.loads(response.text)
        return reasons
    except Exception as e:
        print(f"추천 이유 생성 실패: {e}")
        return {}

# ---------------------------------------
# 6. 헬퍼 함수 및 THE VAULT (수정됨)
# ---------------------------------------
def get_risk_style(level):
    if level == "CRITICAL": return "risk-critical"
    if level == "SERIOUS": return "risk-serious"
    if level == "CAUTION": return "risk-caution"
    return "risk-normal"

def process_and_vault_questionnaire(data):
    """설문 데이터를 봉인하고 해시를 생성합니다. (v5.0 수정)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    # 데이터를 JSON 문자열로 변환
    data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
    # 문자열 기반 해시 생성
    data_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
    
    return {"hash": data_hash, "timestamp": timestamp}

# ---------------------------------------
# 7. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

# IMD Insight 브랜딩 적용
st.title("IMD Insight")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>대한민국 1%를 위한 AI 탐정 & 법률 전략실</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #D4AF37;'>진실은 결코 숨길 수 없다.</p>", unsafe_allow_html=True)
st.markdown("---")

# 세션 상태 관리 (input_step 추가)
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'input_step' not in st.session_state:
    st.session_state.input_step = 1
if 'answers' not in st.session_state:
    st.session_state.answers = {}

# --- Step 1: 서비스 선택 및 데이터 입력 (단계별 설문 방식) ---
if st.session_state.step == 1:
    st.warning("🔒 당신의 기록은 100% 익명이며, 로그는 즉시 파기됩니다.")

    # 서비스 선택 (고정)
    service_type = "💔 배우자 불륜 분석 (외도 가능성 진단)"
    
    # 입력 폼 진행률 표시
    total_steps = 4 # DOSSIER + 3단계 설문
    progress_val = st.session_state.input_step / total_steps
    st.progress(progress_val)

    # --- 입력 Step 1: THE DOSSIER ---
    if st.session_state.input_step == 1:
        st.markdown(f"<h2>1/{total_steps}. 상대방 프로파일링 (THE DOSSIER)</h2>", unsafe_allow_html=True)
        st.info("상대방의 정보를 입력하면 AI가 맞춤형 전략(약점 분석)을 수립합니다.")
        dossier_job = st.text_input("상대방 추정 직업 (예: 공무원, 대기업, 전문직)")
        dossier_personality = st.text_input("상대방 성향 (예: 치밀하고 회피적, 공격적)")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['dossier_job'] = dossier_job
            st.session_state.answers['dossier_personality'] = dossier_personality
            st.session_state.input_step = 2
            st.rerun()

    # --- 입력 Step 2: 행동 패턴 변화 ---
    elif st.session_state.input_step == 2:
        st.markdown(f"<h2>2/{total_steps}. 행동 패턴 변화 분석</h2>", unsafe_allow_html=True)
        q1 = st.radio("Q1. 최근 상대방의 외출/귀가 시간이 불규칙해졌나요? (야근/회식/출장 등)", ("변화 없음", "가끔 증가함", "매우 빈번하게 증가함"), horizontal=True)
        q2 = st.radio("Q2. 주말이나 휴일에 혼자만의 외출이 잦아졌나요?", ("변화 없음", "가끔 있음", "매우 잦음"), horizontal=True)
        q3 = st.radio("Q3. 갑자기 외모 관리(운동, 옷 스타일, 향수)에 신경 쓰는 정도가 늘었나요?", ("변화 없음", "약간 늘어남", "과도하게 신경 씀"), horizontal=True)

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['behavior'] = {"q1_schedule": q1, "q2_weekend": q2, "q3_appearance": q3}
            st.session_state.input_step = 3
            st.rerun()

    # --- 입력 Step 3: 소통 및 관계 변화 ---
    elif st.session_state.input_step == 3:
        st.markdown(f"<h2>3/{total_steps}. 소통 및 관계 변화 분석</h2>", unsafe_allow_html=True)
        q4 = st.radio("Q4. 휴대폰 사용 습관(잠금 강화, 숨김, 통화량 증가)이 변했나요?", ("변화 없음", "약간 의심됨", "확실히 변함"), horizontal=True)
        q5 = st.radio("Q5. 대화 시 방어적이거나 비밀이 많아지고 짜증이 늘었나요?", ("변화 없음", "가끔 그럼", "매우 심해짐"), horizontal=True)
        q6 = st.radio("Q6. 스킨십이나 부부관계 빈도가 눈에 띄게 줄었나요?", ("변화 없음", "약간 줄어듦", "거의 없음"), horizontal=True)

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['communication'] = {"q4_phone": q4, "q5_defensive": q5, "q6_intimacy": q6}
            st.session_state.input_step = 4
            st.rerun()

    # --- 입력 Step 4: 의심 정황 및 증거 ---
    elif st.session_state.input_step == 4:
        st.markdown(f"<h2>4/{total_steps}. 의심 정황 및 증거 현황</h2>", unsafe_allow_html=True)
        q7 = st.radio("Q7. 차량 블랙박스/내비게이션 기록 삭제 흔적 또는 의심스러운 경로가 있나요?", ("확인 안 함/없음", "의심됨", "확실함"), horizontal=True)
        q8 = st.radio("Q8. 설명할 수 없는 지출이나 현금 사용이 늘었나요?", ("확인 안 함/없음", "의심됨", "확실함"), horizontal=True)
        q9 = st.radio("Q9. 물리적인 증거(사진, 카톡 캡처, 영수증 등)를 확보하셨나요?", ("아니오 (심증만 있음)", "약간 확보함", "결정적 증거 확보함"), horizontal=True)


        if st.button("⚡ AI 전략 분석 시작하기", type="primary"):
            st.session_state.answers['evidence'] = {"q7_car": q7, "q8_finance": q8, "q9_physical": q9}
            
            # THE VAULT 실행 (설문 데이터 봉인)
            with st.spinner("🔐 THE VAULT: 입력된 증언을 디지털 금고에 안전하게 봉인 중..."):
                vault_info = process_and_vault_questionnaire(st.session_state.answers)
                time.sleep(1)

            # AI 분석 실행
            dossier_info = f"직업: {st.session_state.answers.get('dossier_job')}, 성향: {st.session_state.answers.get('dossier_personality')}"
            
            with st.spinner("🧠 IMD AI 엔진이 행동 패턴을 분석하고 전략을 수립 중입니다..."):
                # 분석 시 설문 데이터 전달
                analysis_result = perform_ai_analysis(service_type, dossier_info, st.session_state.answers)
            
            # 결과 저장 및 화면 전환
            st.session_state.analysis_result = analysis_result
            st.session_state.vault_info = vault_info
            st.session_state.service_type = service_type
            st.session_state.step = 2
            st.rerun()

# --- Step 2: 분석 결과 확인 및 파트너 매칭 (OMEGA UI) ---
elif st.session_state.step == 2:
    result = st.session_state.analysis_result
    vault_info = st.session_state.get('vault_info', {})

    st.markdown("<h2>📊 IMD Insight - 최종 분석 리포트</h2>", unsafe_allow_html=True)

    if "error" in result:
        st.error(f"❌ 분석 오류 발생: {result['error']}. 잠시 후 다시 시도해주세요.")
        score = 0
        recommended_agencies = []
    
    else:

        # === THE VAULT 확인증 ===
        if vault_info:
            st.markdown("### 🔐 THE VAULT (데이터 봉인 완료)")
            st.markdown('<div class="vault-confirmation">', unsafe_allow_html=True)
            st.text(f"입력된 증언이 안전하게 봉인되었습니다.")
            st.text(f"타임스탬프: {vault_info['timestamp']}")
            st.text(f"고유 해시: {vault_info['hash'][:30]}...")
            st.markdown('</div>', unsafe_allow_html=True)

        
        # === SECTION 1: 스코어 ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("📊 AI 정밀 진단 결과")
        
        risk = result.get('risk_assessment', {})
        score = risk.get('score', 0)
        level = risk.get('level', 'NORMAL')
        summary = risk.get('summary', 'N/A')
        level_class = get_risk_style(level)

        st.markdown(f"### 외도 위험도 (Risk Level)")
        st.markdown(f"<h1 class='{level_class}'>{level} ({score}%)</h1>", unsafe_allow_html=True)
        st.error(f"💬 **AI 코멘트:** {summary}")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === SECTION 2: 상세 분석 (설문 기반) ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("🧐 AI 패턴 해부 (Deep Analysis)")
        analysis = result.get('deep_analysis', {})
        
        st.markdown("#### 1. 행동 변화 패턴 분석")
        st.write(analysis.get('behavioral', {}).get('analysis', 'N/A'))
        st.markdown("---")

        st.markdown("#### 2. 소통 방식 분석")
        st.write(analysis.get('communication', {}).get('analysis', 'N/A'))
        st.markdown("---")

        st.markdown("#### 3. 재정 활동 분석")
        st.write(analysis.get('financial', {}).get('analysis', 'N/A'))
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === THE DOSSIER (인물 파일) ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("📁 THE DOSSIER (대상자 프로파일링)")
        dossier = result.get('the_dossier', {})
        st.markdown(f"**프로파일 분석:** {dossier.get('profile', 'N/A')}")
        st.info(f"💡 **협상 전략 제안:** {dossier.get('negotiation_strategy', 'N/A')}")
        st.markdown('</div>', unsafe_allow_html=True)


        # === SECTION 3: 법적 효력 진단 (The Gap) ===
        st.markdown('<div class="gap-highlight">', unsafe_allow_html=True)
        st.subheader("⚖️ 법적 소송 준비도 (Litigation Readiness)")

        readiness = result.get('litigation_readiness', {})
        suspicion = readiness.get('suspicion_score', score)
        evidence_score = readiness.get('evidence_score', 0)

        col1, col2 = st.columns(2)
        col1.metric(label="심증 (의심 강도)", value=f"{suspicion}%", delta="높음")
        col2.metric(label="물증 (법적 효력)", value=f"{evidence_score}%", delta="매우 부족", delta_color="inverse")

        st.error(f"⚠️ **경고:** {readiness.get('warning', '현재 설문만으로는 법적 증거로 불충분합니다.')}")
        st.markdown(f"🚨 **필요한 결정적 물증:**")
        for item in readiness.get('needed_evidence', []):
            st.markdown(f"- **{item}**")

        st.markdown('</div>', unsafe_allow_html=True)

        # === SECTION 4: THE WAR ROOM (전략 로드맵) ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("⚔️ THE WAR ROOM (단계별 행동 전략)")

        war_room = result.get('the_war_room', {})
        
        st.markdown(f"#### {war_room.get('step1_title', 'Step 1')}")
        st.info(f"Action: {war_room.get('step1_action', 'N/A')}")

        st.markdown(f"#### {war_room.get('step2_title', 'Step 2')}")
        st.warning(f"Action: {war_room.get('step2_action', 'N/A')}")

        st.markdown(f"#### {war_room.get('step3_title', 'Step 3')}")
        st.success(f"Action: {war_room.get('step3_action', 'N/A')}")
        
        st.markdown('</div>', unsafe_allow_html=True)


        # === SECTION 5: 긴급성 ===
        golden = result.get('golden_time', {})
        st.error(f"🚨 **긴급 경고:** {golden.get('urgency_message', '증거가 곧 소멸될 수 있습니다.')}")

        # 분석 성공 시 가중치 기반 3개 추천 실행
        recommended_agencies = get_weighted_unique_recommendations(PARTNER_AGENCIES, k=3)


    # === SECTION 6: 파트너 추천 및 리드 확보 (★v5.0 핵심★) ===
    st.markdown("---")
    st.markdown("<h2>💡 IMD 솔루션 : 검증된 전문가 연결</h2>", unsafe_allow_html=True)
    
    recommended_partners_names = "N/A"

    # 리스크 점수가 40점 이상일 경우 파트너 추천 표시
    if 'error' not in result and score >= 40:
        if recommended_agencies:
            recommended_partners_names = ", ".join([a['name'] for a in recommended_agencies])
            st.error("🚨 분석 결과, 전문가의 즉각적인 개입이 필요합니다. IMD 알고리즘이 귀하의 케이스에 최적화된 전문가 3곳을 선별했습니다.")

            # AI 추천 이유 생성 (★v5.0 핵심★)
            with st.spinner("AI가 맞춤형 추천 이유를 생성 중입니다..."):
                recommendation_reasons = generate_recommendation_reasons(recommended_agencies, result)

            # 추천된 파트너사 목록 표시
            for agency in recommended_agencies:
                # AI가 생성한 이유를 사용, 실패 시 기본 메시지 사용
                reason = recommendation_reasons.get(agency['name'], "IMD 검증 완료된 우수 업체입니다.")
                
                st.markdown(f"""
                <div class="partner-box">
                    <div class="partner-name">{agency['name']}</div>
                    <p><i>"{agency['desc']}"</i></p>
                    <p style="color: #D4AF37;">💡 **AI 추천 이유:** {reason}</p>
                    <p>📞 연락처: <strong>{agency['phone']}</strong></p>
                    <p>🌐 웹사이트: <a href="{agency['url']}" target="_blank" style="color: #AAAAAA;">방문하기</a></p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("⚠️ 위 업체에 연락 시 'IMD Insight 분석 결과'를 보고 연락했다고 말씀하시면 즉각적인 대응이 가능합니다.")

        elif not PARTNER_AGENCIES:
             st.warning("파트너사 데이터를 로드하지 못했습니다. (GitHub URL 확인 필요)")

    # IMD 전략팀 통합 상담 신청 (Fallback Lead Capture)
    st.markdown("---")
    st.markdown("<h3>IMD 전략팀 통합 상담 신청 (무료)</h3>", unsafe_allow_html=True)
    st.info("종합적인 전략 수립(변호사 연계 포함)이 필요하거나, 분석 결과에 대한 추가 상담이 필요한 경우 신청하세요.")

    with st.form(key='lead_form'):
        name = st.text_input("의뢰인 성함 (익명 가능)")
        phone = st.text_input("연락처 (안심 번호 가능)")
        agree = st.checkbox("기밀 유지 및 전문가 매칭에 동의합니다.")
        
        submit_button = st.form_submit_button(label='IMD 전략팀 상담 신청')

        if submit_button:
            if name and phone and agree:
                # 리드 데이터 구성 및 저장 (Google Sheets 연동)
                lead_data = {
                    "timestamp": datetime.now().isoformat(),
                    "name": name,
                    "phone": phone,
                    "risk_score": result.get('risk_assessment', {}).get('score', 'N/A') if 'error' not in result else 'ERROR',
                    "evidence_score": result.get('litigation_readiness', {}).get('evidence_score', 'N/A') if 'error' not in result else 'ERROR',
                    "service_type": st.session_state.service_type,
                    "questionnaire_data": st.session_state.answers,
                    "vault_hash": st.session_state.vault_info.get('hash', 'N/A'),
                    "recommended_partners": recommended_partners_names
                }
                save_success = save_lead_to_google_sheets(lead_data)
                
                if save_success:
                    st.success(f"{name}님, 신청이 완료되었습니다. IMD 전략팀이 즉시 배정되어 연락드릴 예정입니다.")
                else:
                    st.success(f"{name}님, 신청이 완료되었습니다. (시스템 점검으로 인해 연락이 다소 지연될 수 있습니다.)")
                    print(f"LEAD CAPTURE FAILED (GSheet Error): {name}, {phone}")
                
                st.balloons()
            else:
                st.warning("정보 입력 및 약관 동의가 필요합니다.")
