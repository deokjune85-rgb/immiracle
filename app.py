# app.py (IMD Insight v5.1 - Dynamic UX & Persuasion Engine)
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
# Pillow(PIL)과 io는 설문 기반에서는 불필요하나, 추후 이미지 분석 확장을 위해 유지
from PIL import Image
import io
import pandas as pd

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
model = None
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') 
except Exception as e:
    print(f"AI Model Initialization Failed: {e}")
    # API 키 오류 발생 시에도 시스템 작동 유지 (일부 기능 제한)

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
/* 라디오 버튼 스타일링 강화 */
.stRadio > label {
    color: #D4AF37;
    font-weight: bold;
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
/* AI 추천 이유 강조 스타일 (★v5.1 신규★) */
.ai-reason {
    background-color: #3a3a2a;
    border-left: 4px solid #D4AF37;
    padding: 10px;
    margin-top: 10px;
    font-style: italic;
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
            # 데이터 검증
            validated_data = []
            for item in data:
                if isinstance(item, dict) and 'name' in item and 'weight' in item:
                    if not isinstance(item.get('weight'), (int, float)) or item.get('weight', 0) <= 0:
                        item['weight'] = 1
                    validated_data.append(item)
            return validated_data
        return []
    except Exception as e:
        print(f"Error fetching agencies: {e}")
        return []

def get_weighted_unique_recommendations(agencies, k=3):
    """가중치를 기반으로 고유한 파트너사 K개를 선택합니다."""
    if not agencies or k <= 0:
        return []

    if len(agencies) <= k:
        shuffled = list(agencies)
        random.shuffle(shuffled)
        return shuffled

    selected = []
    pool = list(agencies)
    
    for _ in range(k):
        if not pool:
            break
            
        weights = [agency.get('weight', 1) for agency in pool]
        
        try:
            choice = random.choices(pool, weights=weights, k=1)[0]
            selected.append(choice)
            pool.remove(choice)
        except Exception as e:
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
    """설문 기반 AI 분석 프롬프트 정의 (v5.1 Schema)."""
    
    # OMEGA Protocol JSON Schema (v5.1 수정)
    omega_schema = """
    {
      "risk_assessment": {
        "score": (int: 0-100),
        "level": "(string: CRITICAL, SERIOUS, CAUTION, NORMAL)",
        "summary": "(string: 충격적인 상황 요약 및 행동 촉구 메시지)"
      },
      "deep_analysis": {
        "pattern1_title": "(string: 핵심 분석 영역 1 제목. 예: 행동 패턴 변화)",
        "pattern1_analysis": "(string: 분석 내용)",
        "pattern2_title": "(string: 핵심 분석 영역 2 제목. 예: 소통 방식 변화)",
        "pattern2_analysis": "(string: 분석 내용)",
        "pattern3_title": "(string: 핵심 분석 영역 3 제목. 예: 의심 정황 분석)",
        "pattern3_analysis": "(string: 분석 내용)"
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

    # 설문 데이터를 텍스트로 변환 (Dossier 정보 및 자유 서술 포함)
    q_data_text = "\n".join([f"- {q}: {a}" for q, a in questionnaire_data.items()])

    if "💔" in service_type: # 불륜 분석
        return f"""
        [시스템 역할]: AI 기반 외도 위험성 평가 전략가.
        [목표]: 입력된 설문 데이터와 상대방 정보를 기반으로 '불륜 가능성'을 평가하고 전략 로드맵을 제시.
        [분석 지침]:
        1. 입력된 설문조사 결과(자유 서술 포함)를 객관적인 데이터로 간주하고 분석. 응답의 강도를 반영할 것.
        2. 상대방 정보(직업/성향)를 고려하여 'the_dossier'와 'the_war_room'을 맞춤 설계.
        3. ★중요★ 'litigation_readiness.evidence_score'는 극도로 낮게 평가해야 함 (설문은 심증일 뿐 물증이 아님). 물리적 증거 확보의 필요성을 강력히 경고할 것.
        4. 'deep_analysis'의 3가지 영역 제목과 내용을 설문 결과에 맞춰 적절히 생성할 것.
        
        [입력 데이터 요약]
        1. 상대방 직업/성향 (THE DOSSIER 정보): {dossier_info}
        2. [설문조사 결과 및 추가 정황 (증거 데이터)]:
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
        
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {"error": f"AI 분석 중 오류 발생 또는 응답 형식 오류: {e}."}

# ---------------------------------------
# 5. AI 추천 이유 생성기 (★v5.1 강화★)
# ---------------------------------------
def generate_recommendation_reasons(agencies, analysis_result):
    """AI를 사용하여 맞춤형 추천 이유를 생성합니다. (설득력 강화 및 창의성 증대)"""
    
    if not model or not agencies:
        return {}

    # 파트너 정보 포맷팅 및 예상 JSON 구조 생성
    agency_list_text = ""
    expected_json_structure = "{\n"
    for agency in agencies:
        agency_list_text += f"- 업체명: {agency['name']}\n  강점(특징): {agency['desc']}\n"
        # JSON 키 안정성 확보
        safe_key = agency["name"].replace('"', '\\"')
        expected_json_structure += f'  "{safe_key}": "(string: 추천 이유)",\n'
    expected_json_structure = expected_json_structure.rstrip(',\n') + "\n}"

    # 분석 결과 요약 (고객의 약점)
    risk_summary = analysis_result.get('risk_assessment', {}).get('summary', 'N/A')
    needed_evidence = ", ".join(analysis_result.get('litigation_readiness', {}).get('needed_evidence', []))
    dossier_profile = analysis_result.get('the_dossier', {}).get('profile', 'N/A')

    # [★v5.1 강화된 프롬프트★] 전략가 페르소나 및 약점-강점 연결 강조
    prompt = f"""
    [시스템 역할]: 당신은 IMD Insight의 수석 전략 컨설턴트입니다. 목표는 의뢰인이 추천된 전문가(탐정사무소)에게 즉시 연락하도록 설득하는 것입니다.
    [과제]: AI 분석 결과를 바탕으로, 추천된 업체들이 왜 이 의뢰인에게 '유일한 해결책'인지 설명하는 '추천 이유'를 생성하십시오.

    [의뢰인 상황 분석 (약점)]
    - 리스크 요약: {risk_summary}
    - 부족한 증거 (시급): {needed_evidence}
    - 대상자 프로파일: {dossier_profile}

    [추천 대상 업체 목록 (강점)]
    {agency_list_text}

    [작성 지침 - 설득의 기술]:
    1. 각 업체별로 추천 이유를 1~2문장으로 작성합니다.
    2. ★매우 중요★ 업체의 '강점'을 의뢰인의 '약점(부족한 증거, 대상자 성향)'과 직접 연결하여 설득력을 극대화합니다.
       (예: "디지털 증거 확보가 시급하므로, '디지털 포렌식 전문'인 [업체명]의 기술력이 필수적입니다.")
    3. 창의적이고 전문적인 어조를 사용합니다. (환각 허용)

    [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력. Key는 업체명, Value는 추천 이유입니다.
    {expected_json_structure}
    """
    try:
        # 창의성을 위해 Temperature 0.8로 상향 조정, JSON 모드 강제
        generation_config = genai.GenerationConfig(temperature=0.8, response_mime_type="application/json")
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # JSON 파싱 및 검증
        reasons = json.loads(response.text)
        if isinstance(reasons, dict):
            return reasons
        else:
            return {}
    except Exception as e:
        print(f"추천 이유 생성 실패 (JSON 파싱 오류 포함): {e}")
        return {}

# ---------------------------------------
# 6. 헬퍼 함수 및 THE VAULT
# ---------------------------------------
def get_risk_style(level):
    if level == "CRITICAL": return "risk-critical"
    if level == "SERIOUS": return "risk-serious"
    if level == "CAUTION": return "risk-caution"
    return "risk-normal"

def process_and_vault_questionnaire(data):
    """설문 데이터를 봉인하고 해시를 생성합니다."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
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

# 세션 상태 관리
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'input_step' not in st.session_state:
    st.session_state.input_step = 1
if 'answers' not in st.session_state:
    st.session_state.answers = {}

# 서비스 선택 (고정)
service_type = "💔 배우자 불륜 분석 (외도 가능성 진단)"

# --- Step 1: 데이터 입력 (단계별 설문 방식) ---
if st.session_state.step == 1:
    st.warning("🔒 당신의 기록은 100% 익명이며, 로그는 즉시 파기됩니다.")
    
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

    # --- 입력 Step 2: 행동 패턴 변화 (★v5.1 강화★) ---
    elif st.session_state.input_step == 2:
        st.markdown(f"<h2>2/{total_steps}. 행동 패턴 변화 분석</h2>", unsafe_allow_html=True)
        st.info("최근 3개월 기준 상대방의 행동 변화를 체크해주세요.")
        
        st.markdown("#### Q1. 외출 및 귀가 시간의 불규칙성 (야근/회식/출장 등)")
        q1 = st.radio("Q1.", ("변화 없음", "가끔 증가함", "매우 빈번하게 증가함"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q2. 주말이나 휴일의 단독 외출 빈도")
        q2 = st.radio("Q2.", ("변화 없음", "가끔 있음", "매우 잦음"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q3. 외모 관리(운동, 옷 스타일, 향수)에 대한 관심도 증가")
        q3 = st.radio("Q3.", ("변화 없음", "약간 늘어남", "과도하게 신경 씀"), horizontal=True, label_visibility="collapsed")

        if st.button("다음 단계로", type="primary"):
            # 데이터 구조를 평탄화하여 저장 (프롬프트 주입 용이성 확보)
            st.session_state.answers['behavior_q1_schedule'] = q1
            st.session_state.answers['behavior_q2_weekend'] = q2
            st.session_state.answers['behavior_q3_appearance'] = q3
            st.session_state.input_step = 3
            st.rerun()

    # --- 입력 Step 3: 소통 및 관계 변화 (★v5.1 강화★) ---
    elif st.session_state.input_step == 3:
        st.markdown(f"<h2>3/{total_steps}. 소통 및 관계 변화 분석</h2>", unsafe_allow_html=True)
        st.info("상대방과의 관계 및 소통 방식의 변화를 체크해주세요.")

        st.markdown("#### Q4. 휴대폰 사용 습관 변화 (잠금 강화, 숨김, 통화량 증가)")
        q4 = st.radio("Q4.", ("변화 없음", "약간 의심됨", "확실히 변함"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q5. 대화 시 태도 변화 (방어적, 비밀 증가, 짜증 증가)")
        q5 = st.radio("Q5.", ("변화 없음", "가끔 그럼", "매우 심해짐"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q6. 스킨십이나 부부관계 빈도 변화")
        q6 = st.radio("Q6.", ("변화 없음", "약간 줄어듦", "거의 없음"), horizontal=True, label_visibility="collapsed")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['communication_q4_phone'] = q4
            st.session_state.answers['communication_q5_defensive'] = q5
            st.session_state.answers['communication_q6_intimacy'] = q6
            st.session_state.input_step = 4
            st.rerun()

    # --- 입력 Step 4: 의심 정황 및 자유 서술 (★v5.1 동적 안내 시스템★) ---
    elif st.session_state.input_step == 4:
        st.markdown(f"<h2>4/{total_steps}. 의심 정황 및 추가 정보</h2>", unsafe_allow_html=True)
        q7 = st.radio("Q7. 차량 블랙박스/내비게이션 기록 삭제 흔적 또는 의심스러운 경로가 있나요?", ("확인 안 함/없음", "의심됨", "확실함"), horizontal=True)
        q8 = st.radio("Q8. 설명할 수 없는 지출이나 현금 사용이 늘었나요?", ("확인 안 함/없음", "의심됨", "확실함"), horizontal=True)
        
        # [★v5.1 동적 안내 시스템★]
        st.subheader("추가적인 의심 정황 (선택)")
        
        # 이전 단계 답변을 기반으로 동적 Placeholder 생성
        dynamic_placeholder = "AI 분석에 도움이 될 추가 정보를 자유롭게 작성해주세요.\n\n"
        # 평탄화된 데이터 구조에 맞춰 접근 방식 변경
        if st.session_state.answers.get('behavior_q1_schedule') == "매우 빈번하게 증가함":
            dynamic_placeholder += "예: 야근이나 출장이 구체적으로 언제, 어디서 있었는지 알고 계신가요?\n"
        if st.session_state.answers.get('communication_q4_phone') == "확실히 변함":
            dynamic_placeholder += "예: 휴대폰 비밀번호를 바꾸거나 특정 앱을 숨기는 행동이 있었나요?\n"
        if st.session_state.answers.get('behavior_q2_weekend') == "매우 잦음":
             dynamic_placeholder += "예: 주말 외출 시 행선지를 명확히 말하지 않나요?\n"

        q9_freetext = st.text_area(
            "AI 분석 가이드라인",
            height=150,
            placeholder=dynamic_placeholder,
            label_visibility="collapsed"
        )


        if st.button("⚡ AI 전략 분석 시작하기", type="primary"):
            st.session_state.answers['evidence_q7_car'] = q7
            st.session_state.answers['evidence_q8_finance'] = q8
            st.session_state.answers['evidence_q9_freetext'] = q9_freetext
            
            # THE VAULT 실행
            with st.spinner("🔐 THE VAULT: 입력된 증언을 디지털 금고에 안전하게 봉인 중..."):
                vault_info = process_and_vault_questionnaire(st.session_state.answers)
                time.sleep(1)

            # AI 분석 실행
            dossier_info = f"직업: {st.session_state.answers.get('dossier_job')}, 성향: {st.session_state.answers.get('dossier_personality')}"
            
            with st.spinner("🧠 IMD AI 엔진이 행동 패턴을 분석하고 전략을 수립 중입니다..."):
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
        
        st.markdown(f"#### 1. {analysis.get('pattern1_title', '분석 영역 1')}")
        st.write(analysis.get('pattern1_analysis', 'N/A'))
        st.markdown("---")

        st.markdown(f"#### 2. {analysis.get('pattern2_title', '분석 영역 2')}")
        st.write(analysis.get('pattern2_analysis', 'N/A'))
        st.markdown("---")

        st.markdown(f"#### 3. {analysis.get('pattern3_title', '분석 영역 3')}")
        st.write(analysis.get('pattern3_analysis', 'N/A'))
        
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


    # === SECTION 6: 파트너 추천 및 리드 확보 (★v5.1 핵심★) ===
    st.markdown("---")
    st.markdown("<h2>💡 IMD 솔루션 : 검증된 전문가 연결</h2>", unsafe_allow_html=True)
    
    recommended_partners_names = "N/A"

    # 리스크 점수가 40점 이상일 경우 파트너 추천 표시
    if 'error' not in result and score >= 40:
        if recommended_agencies:
            recommended_partners_names = ", ".join([a['name'] for a in recommended_agencies])
            st.error("🚨 분석 결과, 전문가의 즉각적인 개입이 필요합니다. IMD 알고리즘이 귀하의 케이스에 최적화된 전문가 3곳을 선별했습니다.")

            # AI 추천 이유 생성 (★v5.1 핵심★)
            if model:
                with st.spinner("AI가 맞춤형 추천 이유를 생성 중입니다..."):
                    recommendation_reasons = generate_recommendation_reasons(recommended_agencies, result)
            else:
                recommendation_reasons = {}
                st.warning("AI 엔진 연결 문제로 맞춤형 추천 이유 생성이 제한됩니다.")

            # 추천된 파트너사 목록 표시
            for agency in recommended_agencies:
                # AI가 생성한 이유를 사용, 실패 시 기본 메시지 사용
                reason = recommendation_reasons.get(agency['name'])
                if not reason:
                     reason = "IMD 검증 완료된 우수 업체입니다."
                
                st.markdown(f"""
                <div class="partner-box">
                    <div class="partner-name">🏆 {agency['name']}</div>
                    <p><i>"{agency['desc']}"</i></p>
                    <div class="ai-reason">💡 <strong>AI 추천 이유:</strong> {reason}</div>
                    <p style="margin-top: 10px;">📞 연락처: <strong>{agency['phone']}</strong></p>
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
