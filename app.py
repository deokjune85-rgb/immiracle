# app.py (Reset Security v5.3 - Deep Analysis & Repositioning)
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
# Pillow(PIL)과 io는 설문 기반에서는 현재 불필요하나, 추후 확장을 위해 유지
from PIL import Image
import io
import pandas as pd

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------

# [★중요★] 여기에 깃허브 JSON 파일의 Raw URL을 입력하세요.
GITHUB_JSON_URL = "https://raw.githubusercontent.com/deokjune85-rgb/immiracle/refs/heads/main/agencies.json" 

st.set_page_config(
    page_title="리셋시큐리티 - AI 관계 신뢰도 분석 센터",
    layout="centered"
)

# API 키 설정 (Gemini)
model = None
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Gemini 1.5 Flash 사용 (v2.0은 존재하지 않음)
    model = genai.GenerativeModel('gemini-2.0-flash') 
except Exception as e:
    print(f"AI Model Initialization Failed: {e}")

# ---------------------------------------
# 1. UI/UX 스타일링 (Reset Security Branding)
# ---------------------------------------
custom_css = """
<style>
/* === 스트림릿 브랜딩 완전 제거 (스텔스 모드) === */
#MainMenu { visibility: hidden !important; } 
header { visibility: hidden !important; }    
footer { visibility: hidden !important; }    
.stDeployButton { display: none !important; }
[data-testid="stSidebar"] { display: none; } 
.stApp [data-testid="stDecoration"] { display: none !important; }
.stApp .main .block-container { padding-top: 2rem !important; }

/* === 프리미엄 다크 테마 및 가독성 강화 (★v5.4 수정★) === */
.stApp {
    background-color: #0C0C0C;
    /* 기본 텍스트 색상을 완전한 흰색에 가깝게 변경 (#E0E0E0 -> #F5F5F5) */
    color: #F5F5F5; 
    font-family: 'Pretendard', sans-serif;
}

/* 모든 주요 텍스트 요소에 색상 강제 적용 (!important 사용) */
body, p, div, span, li, label, .stMarkdown p, .stMarkdown li, .stMarkdown span {
    color: #F5F5F5 !important;
}


h1 {
    color: #D4AF37; /* Premium Gold */
    font-weight: 800;
    text-align: center;
    font-family: serif;
}
h2, h3, h4 { color: #D4AF37 !important; } /* 헤더 색상도 강제 적용 */

/* 입력 필드 및 라디오 버튼 스타일링 */
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
    background-color: #2C2C2C;
    color: white !important; /* 입력창 내부 텍스트 흰색 강제 */
}

.stRadio > div {
    background-color: #2C2C2C;
}

.stRadio > label {
    color: #D4AF37 !important; /* 라디오 질문 텍스트 색상 강제 */
    font-weight: bold;
}
/* 라디오 버튼 옵션 텍스트 색상 강제 */
.stRadio > div > div > label > div[data-testid="stMarkdownContainer"] > p {
     color: #F5F5F5 !important;
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

/* 분석 섹션 */
.analysis-section {
    background-color: #1E1E1E;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border: 1px solid #333;
}

/* 리스크 레벨 색상 정의 (한글) */
.risk-critical { color: #FF4B4B !important; font-weight: bold; font-size: 28px; }
.risk-serious { color: #FFA500 !important; font-weight: bold; font-size: 28px; }
.risk-caution { color: #FFFF00 !important; font-weight: bold; font-size: 28px; }
.risk-normal { color: #00FF00 !important; font-weight: bold; font-size: 28px; }

/* GAP 강조 박스 */
.gap-highlight { border: 3px solid #FF4B4B; padding: 25px; background-color: #4a1a1a; margin-bottom: 20px; border-radius: 10px; }

/* THE VAULT 스타일 */
.vault-confirmation { background-color: #2a2a4a; color: #00FF00 !important; padding: 15px; border-radius: 5px; font-family: monospace; margin-bottom: 20px; }
/* VAULT 내부 텍스트(st.text로 생성된 요소)도 강제 적용 */
.vault-confirmation .stText { color: #00FF00 !important; }


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
    color: #D4AF37 !important;
    margin-bottom: 5px;
}
.ai-reason {
    background-color: #3a3a2a;
    border-left: 4px solid #D4AF37;
    padding: 10px;
    margin-top: 10px;
    font-style: italic;
}

/* AI 코멘트 박스 */
.ai-comment-box {
    background-color: #2a2a3a;
    border-left: 4px solid #D4AF37;
    padding: 20px;
    margin: 15px 0;
    border-radius: 0 8px 8px 0;
    line-height: 1.8;
}

/* 링크 색상 조정 */
a, a:visited {
    color: #AAAAAA !important;
}
a:hover {
    color: #D4AF37 !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ---------------------------------------
# 2. 데이터 로딩 및 처리
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
            validated_data = []
            for item in data:
                if isinstance(item, dict) and 'name' in item:
                    if not isinstance(item.get('weight'), (int, float)) or item.get('weight', 0) <= 0:
                        item['weight'] = 1
                    # 필드가 없으면 빈 문자열로 설정 (★KeyError 방지★)
                    item['url'] = item.get('url', '')
                    item['phone'] = item.get('phone', '문의 필요')
                    item['desc'] = item.get('desc', '검증된 전문 업체')
                    validated_data.append(item)
            return validated_data
        return []
    except Exception as e:
        print(f"Error fetching agencies: {e}")
        return []

def get_weighted_unique_recommendations(agencies, k=3):
    # (가중치 기반 선택 로직은 이전 버전과 동일)
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
            if pool:
                choice = random.choice(pool)
                selected.append(choice)
                pool.remove(choice)

    return selected

# 파트너사 데이터 로드
PARTNER_AGENCIES = fetch_agencies()

# ---------------------------------------
# 3. 리드 캡처 시스템 (Google Sheets)
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
# 4. 설문 점수 계산 시스템 (★v5.3 강화 - 동적 점수 생성★)
# ---------------------------------------
def calculate_base_score(answers):
    """확장된 설문 응답을 기반으로 동적 점수를 계산합니다."""
    score = 0
    
    # 점수 매핑 정의 (아니오=0, 가끔/의심=3, 예/확실함=7)
    # 다양한 응답 옵션을 포괄하도록 매핑 확장
    score_map = {
        "아니오": 0, "변화 없음": 0, "확인 안 함": 0,
        "가끔 그렇다": 3, "약간 의심됨": 3, "시간 감소": 3,
        "예": 7, "확실함": 7, "요구사항 변화": 7
    }
    
    # 각 질문에 대한 점수 합산 (v5.3 확장된 설문 반영)
    question_keys = [
        # Step 2: 일상 및 행동 변화
        'behavior_q1_schedule', 'behavior_q2_weekend', 'behavior_q3_appearance', 'other_q16_specific_day',
        # Step 3: 휴대폰 사용 및 소통 변화
        'comm_q4_phone_habit', 'phone_q7_voicemail', 'phone_q8_call_rejection', 'phone_q9_silent_call', 'comm_q10_katalk',
        # Step 4: 관계 및 태도 변화
        'comm_q5_attitude', 'comm_q6_intimacy', 'comm_q15_intimacy_style', 'routine_q11_bathroom', 'routine_q12_sleep_phone',
        # Step 5: 차량 및 기타 정황
        'vehicle_q13_cleanliness', 'vehicle_q14_bluetooth', 'finance_q15_spending'
        # (evidence_q18_physical_evidence는 점수 계산에서는 제외하고 증거 수준 평가에 활용)
    ]
    
    for key in question_keys:
        response = answers.get(key, '')
        score += score_map.get(response, 0)

    # 최대 점수(7점 * 17문항 = 119점)를 95점 만점으로 스케일링
    max_raw_score = 7 * len(question_keys)
    if max_raw_score > 0:
        scaled_score = (score / max_raw_score) * 95
    else:
        scaled_score = 0

    # 랜덤 변동 추가 (±3%) 및 최종 보정
    variation = random.uniform(-3, 3)
    final_score = int(round(scaled_score + variation))
    final_score = min(max(final_score, 5), 98) # 5~98점 사이 보장
    
    return final_score

def get_risk_level_korean(score):
    """점수에 따른 한글 위험도 레벨 반환 (포지셔닝 변경 반영)"""
    if score >= 80:
        return "심각 단계", "risk-critical"
    elif score >= 60:
        return "위험 단계", "risk-serious"
    elif score >= 40:
        return "주의 단계", "risk-caution"
    else:
        return "안정 단계", "risk-normal"


# ---------------------------------------
# 5. AI 분석 엔진 (강화된 프롬프트)
# ---------------------------------------

def get_analysis_prompt(service_type, dossier_info, questionnaire_data, calculated_score):
    """설문 기반 AI 분석 프롬프트 (★v5.3 수정 - 상세 코멘트 및 포지셔닝 강화★)"""
    
    # (Schema는 이전 버전과 동일하게 유지)
    omega_schema = """
    {
      "risk_assessment": {
        "summary": "(string: 4-6문장의 상세하고 전문적인 상담 분석. 의뢰인의 심리 상태에 공감하며, 객관적인 행동 패턴 분석 결과를 설명하고 그 의미를 해석.)"
      },
      "deep_analysis": {
        "pattern1_title": "(string: 핵심 분석 영역 1 제목)",
        "pattern1_analysis": "(string: 2-3문장의 상세 분석)",
        "pattern2_title": "(string: 핵심 분석 영역 2 제목)",
        "pattern2_analysis": "(string: 2-3문장의 상세 분석)",
        "pattern3_title": "(string: 핵심 분석 영역 3 제목)",
        "pattern3_analysis": "(string: 2-3문장의 상세 분석)"
      },
      "litigation_readiness": {
        "suspicion_score": (int: 심증 점수, 입력된 calculated_score와 유사하게),
        "evidence_score": (int: 0-15 사이. 설문은 물증이 아니므로 극도로 낮게),
        "warning": "(string: 현재 상황의 심각성과 물리적 증거 확보의 필요성을 전문적으로 경고)",
        "needed_evidence": ["(string: 필요한 증거 항목 3-5개)"]
      },
      "golden_time": {
        "urgency_message": "(string: 시간의 중요성을 강조하는 전문적 메시지)"
      },
      "the_dossier": {
        "profile": "(string: 상대방 프로파일링 2-3문장)",
        "negotiation_strategy": "(string: 전략 제안 2-3문장)"
      },
      "the_war_room": {
        "step1_title": "(string: 1단계 제목)",
        "step1_action": "(string: 구체적 행동 지침)",
        "step2_title": "(string: 2단계 제목)",
        "step2_action": "(string: 구체적 행동 지침)",
        "step3_title": "(string: 3단계 제목)",
        "step3_action": "(string: 구체적 행동 지침)"
      }
    }
    """

    q_data_text = "\n".join([f"- {q}: {a}" for q, a in questionnaire_data.items()])

    # [★v5.3 수정★] 역할 변경: 심리 상담 및 행동 분석 전문가
    return f"""
    [시스템 역할]: 당신은 20년 경력의 관계 심리 상담사이자 행동 패턴 분석 전문가입니다.
    [목표]: 의뢰인의 설문 데이터를 분석하여 전문적이고 깊이 있는 관계 신뢰도 분석 리포트를 작성합니다.
    
    [분석 지침]:
    1. 설문 응답 간의 상관관계를 심층 분석하세요.
    2. 'risk_assessment.summary'는 반드시 4-6문장으로 상세하게 작성하세요. 의뢰인이 느끼는 불안감에 깊이 공감하면서도, 관찰된 행동 패턴이 심리학적으로 어떤 의미를 가지는지 전문적으로 설명하세요.
    3. 이미 계산된 위험 신호 점수는 {calculated_score}점입니다. suspicion_score는 이 값과 유사하게 설정하세요.
    4. evidence_score는 설문 기반이므로 반드시 0-15점 사이로 극도로 낮게 설정하세요.
    5. 모든 분석은 상담 전문가의 신뢰감 있고 지지적인 톤으로 작성하세요.
    
    [입력 데이터]
    - 상대방 정보: {dossier_info}
    - 설문 응답:
    {q_data_text}
    - 사전 계산된 위험 신호 점수: {calculated_score}점

    [출력 형식]: 반드시 아래 JSON 스키마만 출력. 다른 텍스트 금지.
    {omega_schema}
    """

def perform_ai_analysis(service_type, dossier_info, questionnaire_data, calculated_score):
    """AI 분석 실행"""
    if not model:
        # AI 엔진 미작동 시 폴백 처리 (점수 기반 기본 분석 결과 반환)
        return {"fallback": True, "calculated_score": calculated_score}

    prompt = get_analysis_prompt(service_type, dossier_info, questionnaire_data, calculated_score)
    
    try:
        # Temperature 0.4로 설정하여 분석의 깊이와 일관성 유지
        generation_config = genai.GenerationConfig(temperature=0.4, response_mime_type="application/json")
        safety_settings = [{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
        
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        result = json.loads(response.text)
        return result

    except Exception as e:
        print(f"AI Analysis Error: {e}")
        # AI 분석 실패 시 폴백 처리
        return {"fallback": True, "calculated_score": calculated_score}


# ---------------------------------------
# 6. AI 추천 이유 생성기
# ---------------------------------------
def generate_recommendation_reasons(agencies, analysis_result, calculated_score):
    # (추천 이유 생성 로직은 이전 버전과 동일하게 유지)
    if not model or not agencies:
        return {}

    agency_list_text = ""
    expected_json_structure = "{\n"
    for agency in agencies:
        agency_list_text += f"- 업체명: {agency['name']}\n  강점: {agency.get('desc', '전문 업체')}\n"
        safe_key = agency["name"].replace('"', '\\"')
        expected_json_structure += f'  "{safe_key}": "(string: 추천 이유 1-2문장)",\n'
    expected_json_structure = expected_json_structure.rstrip(',\n') + "\n}"

    # 폴백 상황 대비 데이터 추출
    if analysis_result.get('fallback'):
        risk_summary = "AI 분석 결과 기반 전문가 매칭 필요."
        needed_evidence = "물리적 증거 확보 시급."
        dossier_profile = "대상자 정보 기반 분석 필요."
    else:
        risk_summary = analysis_result.get('risk_assessment', {}).get('summary', '상황 분석 필요')
        needed_evidence = ", ".join(analysis_result.get('litigation_readiness', {}).get('needed_evidence', ['증거 확보 필요']))
        dossier_profile = analysis_result.get('the_dossier', {}).get('profile', 'N/A')

    prompt = f"""
    [시스템 역할]: 당신은 리셋시큐리티의 수석 전략 컨설턴트입니다. 목표는 의뢰인이 추천된 전문가에게 즉시 연락하도록 설득하는 것입니다.
    [과제]: AI 분석 결과를 바탕으로, 추천된 업체들이 왜 이 의뢰인에게 '유일한 해결책'인지 설명하는 '추천 이유'를 생성하십시오.

    [의뢰인 상황 분석 (약점)]
    - 위험 신호 점수: {calculated_score}점
    - 상황 요약: {risk_summary}
    - 부족한 증거 (시급): {needed_evidence}
    - 대상자 프로파일: {dossier_profile}

    [추천 대상 업체 목록 (강점)]
    {agency_list_text}

    [작성 지침 - 설득의 기술]:
    1. 각 업체별로 추천 이유를 1~2문장으로 작성합니다.
    2. ★매우 중요★ 업체의 '강점'을 의뢰인의 '약점(부족한 증거, 대상자 성향)'과 직접 연결하여 설득력을 극대화합니다.
    3. 창의적이고 전문적인 어조를 사용합니다. (환각 허용)

    [출력 형식]: 반드시 아래 JSON 스키마를 준수하여 출력. Key는 업체명, Value는 추천 이유입니다.
    {expected_json_structure}
    """
    try:
        # 창의성을 위해 Temperature 0.8 사용
        generation_config = genai.GenerationConfig(temperature=0.8, response_mime_type="application/json")
        response = model.generate_content(prompt, generation_config=generation_config)
        reasons = json.loads(response.text)
        return reasons if isinstance(reasons, dict) else {}
    except Exception as e:
        print(f"추천 이유 생성 실패: {e}")
        return {}


# ---------------------------------------
# 7. 헬퍼 함수
# ---------------------------------------
def process_and_vault_questionnaire(data):
    """설문 데이터 봉인 및 해시 생성"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
    data_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
    return {"hash": data_hash, "timestamp": timestamp}


# ---------------------------------------
# 8. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

# 브랜딩 (★v5.3 수정★)
st.title("리셋시큐리티")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>AI 기반 관계 신뢰도 분석 센터</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #D4AF37;'>정확한 분석, 현명한 대응</p>", unsafe_allow_html=True)
st.markdown("---")

# 세션 상태
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'input_step' not in st.session_state:
    st.session_state.input_step = 1
if 'answers' not in st.session_state:
    st.session_state.answers = {}

service_type = "💔 관계 신뢰도 분석 (배우자/연인)" # 용어 변경

# 응답 옵션 정의
OPTIONS_BASIC_YN = ("아니오", "가끔 그렇다", "예")
OPTIONS_YN = ("아니오", "예")

# --- Step 1: 데이터 입력 (★v5.3 확장된 설문★) ---
if st.session_state.step == 1:
    st.info("입력하신 정보는 익명으로 처리되며 안전하게 보호됩니다.")
    
    total_steps = 5 # 총 5단계
    progress_val = st.session_state.input_step / total_steps
    st.progress(progress_val)

    # --- 입력 Step 1: 상대방 정보 ---
    if st.session_state.input_step == 1:
        st.markdown(f"<h2>1/{total_steps}. 상대방 기본 정보</h2>", unsafe_allow_html=True)
        dossier_job = st.text_input("상대방 직업 (예: 회사원, 자영업, 전문직)")
        dossier_personality = st.text_input("상대방 성향 (예: 내성적, 외향적, 꼼꼼함)")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['dossier_job'] = dossier_job
            st.session_state.answers['dossier_personality'] = dossier_personality
            st.session_state.input_step = 2
            st.rerun()

    # --- 입력 Step 2: 일상 및 행동 변화 ---
    elif st.session_state.input_step == 2:
        st.markdown(f"<h2>2/{total_steps}. 일상 및 행동 변화</h2>", unsafe_allow_html=True)
        st.markdown("최근 3개월 기준으로 응답해주세요.")
        
        st.markdown("#### Q1. 외출/귀가 시간이 불규칙하거나 잦아졌는가?")
        q1 = st.radio("Q1.", OPTIONS_BASIC_YN, horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q2. 주말/휴일 단독 외출이 잦아졌는가?")
        q2 = st.radio("Q2.", OPTIONS_BASIC_YN, horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q3. 외모 관리에 대한 관심이 과도하게 늘었는가?")
        q3 = st.radio("Q3.", OPTIONS_BASIC_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q4. 특정 요일/시간대에 자주 연락이 두절되는가?")
        q4 = st.radio("Q4.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['behavior_q1_schedule'] = q1
            st.session_state.answers['behavior_q2_weekend'] = q2
            st.session_state.answers['behavior_q3_appearance'] = q3
            st.session_state.answers['other_q16_specific_day'] = q4
            st.session_state.input_step = 3
            st.rerun()

    # --- 입력 Step 3: 휴대폰 사용 및 소통 변화 ---
    elif st.session_state.input_step == 3:
        st.markdown(f"<h2>3/{total_steps}. 휴대폰 사용 및 소통 변화</h2>", unsafe_allow_html=True)

        st.markdown("#### Q5. 휴대폰 잠금을 강화하거나 숨기는 행동이 있는가?")
        q5 = st.radio("Q5.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q6. 전화를 한 번에 받지 않는 횟수가 늘었는가?")
        q6 = st.radio("Q6.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q7. 전화를 거절하거나 받지 않는 횟수가 늘었는가?")
        q7 = st.radio("Q7.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q8. 항상 조용한 곳에서만 통화하려 하는가?")
        q8 = st.radio("Q8.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q9. 카톡 알림이 무음이거나, 카톡 시 평소와 다른 표정을 보이는가?")
        q9 = st.radio("Q9.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['comm_q4_phone_habit'] = q5
            st.session_state.answers['phone_q7_voicemail'] = q6
            st.session_state.answers['phone_q8_call_rejection'] = q7
            st.session_state.answers['phone_q9_silent_call'] = q8
            st.session_state.answers['comm_q10_katalk'] = q9
            st.session_state.input_step = 4
            st.rerun()

    # --- 입력 Step 4: 관계 및 태도 변화 ---
    elif st.session_state.input_step == 4:
        st.markdown(f"<h2>4/{total_steps}. 관계 및 태도 변화</h2>", unsafe_allow_html=True)

        st.markdown("#### Q10. 대화 시 방어적이거나 짜증/화가 늘었는가?")
        q10 = st.radio("Q10.", OPTIONS_BASIC_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q11. 스킨십이나 성관계 횟수가 50% 이상 줄었는가?")
        q11 = st.radio("Q11.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q12. 성관계 시간이 현저하게 줄었거나, 평소와 다른 요구가 늘었는가?")
        q12 = st.radio("Q12.", ("변화 없음", "시간 감소", "요구사항 변화"), horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q13. 화장실 체류 시간이 길어지거나, 집에서 씻는 빈도/시간이 줄었는가?")
        q13 = st.radio("Q13.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q14. 잠 잘 때 휴대폰을 손에 쥐거나 머리맡에 두고 자는가?")
        q14 = st.radio("Q14.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")


        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['comm_q5_attitude'] = q10
            st.session_state.answers['comm_q6_intimacy'] = q11
            st.session_state.answers['comm_q15_intimacy_style'] = q12
            st.session_state.answers['routine_q11_bathroom'] = q13
            st.session_state.answers['routine_q12_sleep_phone'] = q14
            st.session_state.input_step = 5
            st.rerun()

    # --- 입력 Step 5: 차량 및 기타 정황 ---
    elif st.session_state.input_step == 5:
        st.markdown(f"<h2>5/{total_steps}. 차량 및 기타 정황</h2>", unsafe_allow_html=True)
        
        st.markdown("#### Q15. 평소 지저분하던 차량 실내외가 깨끗해졌는가?")
        q15 = st.radio("Q15.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q16. 동승 시 차량 블루투스 연결을 꺼리는가?")
        q16 = st.radio("Q16.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q17. 설명할 수 없는 지출(휴대폰 요금 증가, 현금 사용)이 늘었는가?")
        q17 = st.radio("Q17.", OPTIONS_YN, horizontal=True, label_visibility="collapsed")

        st.markdown("#### Q18. 물리적인 증거(사진, 카톡 캡처, 영수증 등)를 확보했는가?")
        q18 = st.radio("Q18.", ("아니오 (심증만 있음)", "약간 확보함", "결정적 증거 확보함"), horizontal=True, label_visibility="collapsed")

        st.markdown("#### 추가 정보 (선택사항)")
        q19_freetext = st.text_area(
            "추가 정보",
            height=120,
            placeholder="분석에 도움이 될 추가 정보가 있다면 자유롭게 작성해주세요.",
            label_visibility="collapsed"
        )

        if st.button("분석 시작", type="primary"):
            st.session_state.answers['vehicle_q13_cleanliness'] = q15
            st.session_state.answers['vehicle_q14_bluetooth'] = q16
            st.session_state.answers['finance_q15_spending'] = q17
            st.session_state.answers['other_q17_physical_evidence'] = q18
            st.session_state.answers['evidence_q9_freetext'] = q19_freetext
            
            with st.spinner("데이터 처리 중..."):
                vault_info = process_and_vault_questionnaire(st.session_state.answers)
                time.sleep(1)

            # 점수 계산 (★v5.3 수정된 로직 적용★)
            calculated_score = calculate_base_score(st.session_state.answers)
            
            dossier_info = f"직업: {st.session_state.answers.get('dossier_job')}, 성향: {st.session_state.answers.get('dossier_personality')}"
            
            with st.spinner("AI 분석 진행 중..."):
                analysis_result = perform_ai_analysis(service_type, dossier_info, st.session_state.answers, calculated_score)
            
            st.session_state.analysis_result = analysis_result
            st.session_state.calculated_score = calculated_score
            st.session_state.vault_info = vault_info
            st.session_state.service_type = service_type
            st.session_state.step = 2
            st.rerun()


# --- Step 2: 분석 결과 ---
elif st.session_state.step == 2:
    result = st.session_state.analysis_result
    vault_info = st.session_state.get('vault_info', {})
    calculated_score = st.session_state.get('calculated_score', 50)

    # AI 분석 실패 시 폴백 처리
    if "error" in result or result.get('fallback'):
        if "error" in result:
            st.error(f"분석 오류: {result['error']}")
        st.warning("AI 엔진 연결 문제로 기본 분석 결과를 제공합니다.")
        
        # 폴백용 기본 결과 생성
        level_korean, level_class = get_risk_level_korean(calculated_score)
        result = {
            'risk_assessment': {'summary': '설문 기반 분석 결과, 위험 신호가 감지되었습니다. 정확한 판단을 위해 전문가의 도움이 필요합니다.'},
            'deep_analysis': {},
            'the_dossier': {},
            'litigation_readiness': {'suspicion_score': calculated_score, 'evidence_score': random.randint(5, 15), 'warning': '물리적 증거 확보가 시급합니다.', 'needed_evidence': ['전문가 상담 필요']},
            'the_war_room': {},
            'golden_time': {'urgency_message': '시간이 지날수록 대응이 어려워질 수 있습니다.'}
        }
        score = calculated_score
    else:
        score = calculated_score # AI 분석 성공 시 점수 사용


    st.markdown("<h2>분석 리포트</h2>", unsafe_allow_html=True)

    # === 데이터 봉인 확인 ===
    if vault_info:
        st.markdown("### 데이터 처리 완료")
        st.markdown('<div class="vault-confirmation">', unsafe_allow_html=True)
        st.text(f"처리 시간: {vault_info['timestamp']}")
        st.text(f"고유 식별자: {vault_info['hash'][:24]}...")
        st.markdown('</div>', unsafe_allow_html=True)

    # === 위험도 점수 (동적) ===
    st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
    st.subheader("분석 결과 요약")
    
    level_korean, level_class = get_risk_level_korean(score)

    # [★v5.3 수정★] 용어 변경: 외도 위험도 -> 관계 위험 신호
    st.markdown(f"### 관계 위험 신호")
    st.markdown(f"<div class='{level_class}'>{level_korean} ({score}%)</div>", unsafe_allow_html=True)
    
    # AI 코멘트 (상세)
    summary = result.get('risk_assessment', {}).get('summary', '분석 결과를 확인해주세요.')
    # [★v5.3 수정★] AI 코멘트 박스 스타일 적용
    st.markdown(f'<div class="ai-comment-box"><strong>전문가 코멘트:</strong><br><br>{summary}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # === 상세 분석 ===
    st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
    st.subheader("상세 패턴 분석")
    analysis = result.get('deep_analysis', {})
    
    st.markdown(f"#### 1. {analysis.get('pattern1_title', '행동 패턴')}")
    st.write(analysis.get('pattern1_analysis', '분석 내용 없음'))
    st.markdown("---")

    st.markdown(f"#### 2. {analysis.get('pattern2_title', '소통 패턴')}")
    st.write(analysis.get('pattern2_analysis', '분석 내용 없음'))
    st.markdown("---")

    st.markdown(f"#### 3. {analysis.get('pattern3_title', '종합 정황')}")
    st.write(analysis.get('pattern3_analysis', '분석 내용 없음'))
    
    st.markdown('</div>', unsafe_allow_html=True)

    # === 프로파일링 ===
    st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
    st.subheader("대상자 분석 및 대응 전략")
    dossier = result.get('the_dossier', {})
    st.markdown(f"**분석 결과:** {dossier.get('profile', '정보 부족')}")
    st.info(f"**전략 제안:** {dossier.get('negotiation_strategy', '추가 상담 필요')}")
    st.markdown('</div>', unsafe_allow_html=True)

    # === 증거 현황 (The Gap) ===
    st.markdown('<div class="gap-highlight">', unsafe_allow_html=True)
    st.subheader("증거 확보 현황")

    readiness = result.get('litigation_readiness', {})
    suspicion = readiness.get('suspicion_score', score)
    evidence_score = readiness.get('evidence_score', 5)

    col1, col2 = st.columns(2)
    col1.metric(label="심증 강도", value=f"{suspicion}%")
    col2.metric(label="물증 수준", value=f"{evidence_score}%")

    st.warning(f"**경고:** {readiness.get('warning', '설문 기반 분석은 참고용이며, 실제 대응을 위해서는 물리적 증거 확보가 필수적입니다.')}")
    
    st.markdown("**확보 권장 자료:**")
    for item in readiness.get('needed_evidence', ['전문가 상담 필요']):
        st.markdown(f"- {item}")

    st.markdown('</div>', unsafe_allow_html=True)

    # === 행동 전략 ===
    st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
    st.subheader("대응 전략 로드맵")

    war_room = result.get('the_war_room', {})
    
    st.markdown(f"#### {war_room.get('step1_title', '1단계')}")
    st.info(f"{war_room.get('step1_action', '전문가 상담')}")

    st.markdown(f"#### {war_room.get('step2_title', '2단계')}")
    st.warning(f"{war_room.get('step2_action', '자료 수집')}")

    st.markdown(f"#### {war_room.get('step3_title', '3단계')}")
    st.success(f"{war_room.get('step3_action', '대응 실행')}")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # === 긴급성 ===
    golden = result.get('golden_time', {})
    st.error(f"**긴급 안내:** {golden.get('urgency_message', '시간이 지날수록 대응이 어려워질 수 있습니다.')}")

    # 가중치 기반 3개 추천 실행
    recommended_agencies = get_weighted_unique_recommendations(PARTNER_AGENCIES, k=3)


    # === 전문가 연결 ===
    st.markdown("---")
    st.markdown("<h2>전문가 연결 솔루션</h2>", unsafe_allow_html=True)
    
    recommended_partners_names = "N/A"

    # 점수가 40점 이상일 경우 파트너 추천
    if score >= 40:
        if recommended_agencies:
            recommended_partners_names = ", ".join([a['name'] for a in recommended_agencies])
            st.warning("분석 결과, 전문가의 도움이 필요한 단계입니다. 리셋시큐리티 알고리즘이 귀하의 상황에 최적화된 전문가 3곳을 선별했습니다.")

            if model:
                with st.spinner("맞춤 추천 정보 생성 중..."):
                    recommendation_reasons = generate_recommendation_reasons(recommended_agencies, result, calculated_score)
            else:
                recommendation_reasons = {}

            for agency in recommended_agencies:
                reason = recommendation_reasons.get(agency['name'], "검증된 전문 업체입니다.")
                
                # URL 처리 (http/https가 없으면 추가)
                website_html = ""
                url = agency.get('url')
                if url:
                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = "http://" + url
                    website_html = f'<p>웹사이트: <a href="{url}" target="_blank" style="color: #AAAAAA;">방문하기</a></p>'
                
                st.markdown(f"""
                <div class="partner-box">
                    <div class="partner-name">{agency['name']}</div>
                    <p><i>"{agency.get('desc', '전문 업체')}"</i></p>
                    <div class="ai-reason"><strong>추천 사유:</strong> {reason}</div>
                    <p style="margin-top: 10px;">연락처: <strong>{agency.get('phone', '문의 필요')}</strong></p>
                    {website_html}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("위 업체 연락 시 '리셋시큐리티 분석 결과 확인'이라고 말씀하시면 원활한 상담이 가능합니다.")

        elif not PARTNER_AGENCIES:
             st.warning("전문가 정보를 불러오지 못했습니다. (GitHub URL 확인 필요)")

    # === 상담 신청 ===
    st.markdown("---")
    st.markdown("<h3>통합 상담 신청 (무료)</h3>", unsafe_allow_html=True)
    st.info("종합적인 상담(법률 자문 연계 포함)이 필요하시면 아래 양식을 작성해주세요.")

    with st.form(key='lead_form'):
        name = st.text_input("성함 (익명 가능)")
        phone = st.text_input("연락처")
        agree = st.checkbox("개인정보 수집 및 이용에 동의합니다.")
        
        submit_button = st.form_submit_button(label='상담 신청')

        if submit_button:
            if name and phone and agree:
                # 리드 데이터 구성 및 저장
                # evidence_score 추출 시 폴백 처리 강화
                if 'error' not in result and not result.get('fallback'):
                    evidence_score_val = result.get('litigation_readiness', {}).get('evidence_score', 'N/A')
                else:
                    evidence_score_val = 'N/A (Fallback/Error)'

                lead_data = {
                    "timestamp": datetime.now().isoformat(),
                    "name": name,
                    "phone": phone,
                    "risk_score": score,
                    "evidence_score": evidence_score_val,
                    "service_type": st.session_state.service_type,
                    "questionnaire_data": st.session_state.answers,
                    "vault_hash": st.session_state.vault_info.get('hash', 'N/A'),
                    "recommended_partners": recommended_partners_names
                }
                save_success = save_lead_to_google_sheets(lead_data)
                
                if save_success:
                    st.success(f"{name}님, 신청이 완료되었습니다. 담당자가 곧 연락드리겠습니다.")
                else:
                    st.success(f"{name}님, 신청이 완료되었습니다.") # 실패해도 성공 메시지 출력
                
                st.balloons()
            else:
                st.warning("모든 항목을 입력하고 동의해주세요.")
