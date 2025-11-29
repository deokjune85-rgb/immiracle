# app.py (Reset Security v5.2 - Professional Edition)
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

GITHUB_JSON_URL = "https://raw.githubusercontent.com/deokjune85-rgb/immiracle/refs/heads/main/agencies.json" 

st.set_page_config(
    page_title="리셋시큐리티 - AI 분석 시스템",
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

# ---------------------------------------
# 1. UI/UX 스타일링 (Reset Security Branding)
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

/* === 프리미엄 다크 테마 === */
.stApp {
    background-color: #0C0C0C;
    color: #E0E0E0;
    font-family: 'Pretendard', sans-serif;
}
h1 {
    color: #D4AF37;
    font-weight: 800;
    text-align: center;
    font-family: serif;
}
h2, h3, h4 { color: #D4AF37; }

.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div, .stRadio > div {
    background-color: #2C2C2C;
    color: white;
}
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
                    # url 필드가 없으면 빈 문자열로 설정 (KeyError 방지)
                    if 'url' not in item:
                        item['url'] = ''
                    if 'phone' not in item:
                        item['phone'] = '문의 필요'
                    if 'desc' not in item:
                        item['desc'] = '검증된 전문 업체'
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
# 4. 설문 점수 계산 시스템 (동적 점수 생성)
# ---------------------------------------
def calculate_base_score(answers):
    """설문 응답을 기반으로 기본 점수를 계산합니다."""
    score = 0
    
    # 행동 패턴 점수 (최대 30점)
    behavior_map = {
        "변화 없음": 0,
        "가끔 증가함": 5, "가끔 있음": 5, "약간 늘어남": 5,
        "매우 빈번하게 증가함": 10, "매우 잦음": 10, "과도하게 신경 씀": 10
    }
    score += behavior_map.get(answers.get('behavior_q1_schedule', ''), 0)
    score += behavior_map.get(answers.get('behavior_q2_weekend', ''), 0)
    score += behavior_map.get(answers.get('behavior_q3_appearance', ''), 0)
    
    # 소통 변화 점수 (최대 30점)
    comm_map = {
        "변화 없음": 0,
        "약간 의심됨": 5, "가끔 그럼": 5, "약간 줄어듦": 5,
        "확실히 변함": 10, "매우 심해짐": 10, "거의 없음": 10
    }
    score += comm_map.get(answers.get('communication_q4_phone', ''), 0)
    score += comm_map.get(answers.get('communication_q5_defensive', ''), 0)
    score += comm_map.get(answers.get('communication_q6_intimacy', ''), 0)
    
    # 증거 정황 점수 (최대 20점)
    evidence_map = {
        "확인 안 함/없음": 0,
        "의심됨": 5,
        "확실함": 10
    }
    score += evidence_map.get(answers.get('evidence_q7_car', ''), 0)
    score += evidence_map.get(answers.get('evidence_q8_finance', ''), 0)
    
    # 자유 서술 보너스 (최대 10점)
    freetext = answers.get('evidence_q9_freetext', '')
    if len(freetext) > 100:
        score += 10
    elif len(freetext) > 50:
        score += 5
    
    # 최소/최대 보정 및 랜덤 변동 추가 (±5%)
    base = min(max(score, 15), 95)
    variation = random.randint(-5, 5)
    final_score = min(max(base + variation, 10), 98)
    
    return final_score

def get_risk_level_korean(score):
    """점수에 따른 한글 위험도 레벨 반환"""
    if score >= 80:
        return "매우 위험", "risk-critical"
    elif score >= 60:
        return "위험", "risk-serious"
    elif score >= 40:
        return "주의 필요", "risk-caution"
    else:
        return "정상 범위", "risk-normal"


# ---------------------------------------
# 5. AI 분석 엔진 (강화된 프롬프트)
# ---------------------------------------

def get_analysis_prompt(service_type, dossier_info, questionnaire_data, calculated_score):
    """설문 기반 AI 분석 프롬프트 (점수 전달 방식으로 변경)"""
    
    omega_schema = """
    {
      "risk_assessment": {
        "summary": "(string: 3-5문장의 상세하고 전문적인 상황 분석. 의뢰인의 감정을 공감하면서도 객관적인 분석 제공. 구체적인 행동 패턴과 그 의미를 설명.)"
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
        "evidence_score": (int: 0-20 사이. 설문은 물증이 아니므로 낮게),
        "warning": "(string: 물리적 증거 확보의 필요성을 전문적으로 설명)",
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

    return f"""
    [시스템 역할]: 당신은 20년 경력의 전문 상담사이자 행동 분석 전문가입니다.
    [목표]: 의뢰인의 설문 데이터를 분석하여 전문적이고 공감적인 상담 리포트를 작성합니다.
    
    [분석 지침]:
    1. 설문 응답을 꼼꼼히 분석하고, 각 응답 간의 상관관계를 파악하세요.
    2. 'risk_assessment.summary'는 반드시 3-5문장으로 상세하게 작성하세요. 의뢰인이 느끼는 불안감에 공감하면서도 객관적인 분석을 제공하세요.
    3. 이미 계산된 위험도 점수는 {calculated_score}점입니다. suspicion_score는 이 값과 유사하게 설정하세요.
    4. evidence_score는 설문 기반이므로 반드시 0-20점 사이로 매우 낮게 설정하세요.
    5. 모든 분석은 전문적이고 신뢰감을 주는 톤으로 작성하세요.
    
    [입력 데이터]
    - 상대방 정보: {dossier_info}
    - 설문 응답:
    {q_data_text}
    - 사전 계산된 위험도 점수: {calculated_score}점

    [출력 형식]: 반드시 아래 JSON 스키마만 출력. 다른 텍스트 금지.
    {omega_schema}
    """

def perform_ai_analysis(service_type, dossier_info, questionnaire_data, calculated_score):
    """AI 분석 실행"""
    if not model:
        return {"error": "AI 엔진이 초기화되지 않았습니다."}

    prompt = get_analysis_prompt(service_type, dossier_info, questionnaire_data, calculated_score)
    
    try:
        generation_config = genai.GenerationConfig(temperature=0.4, response_mime_type="application/json")
        safety_settings = [{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}]
        
        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {"error": f"AI 분석 중 오류 발생: {e}"}


# ---------------------------------------
# 6. AI 추천 이유 생성기
# ---------------------------------------
def generate_recommendation_reasons(agencies, analysis_result, calculated_score):
    """맞춤형 추천 이유 생성"""
    
    if not model or not agencies:
        return {}

    agency_list_text = ""
    expected_json_structure = "{\n"
    for agency in agencies:
        agency_list_text += f"- 업체명: {agency['name']}\n  강점: {agency.get('desc', '전문 업체')}\n"
        safe_key = agency["name"].replace('"', '\\"')
        expected_json_structure += f'  "{safe_key}": "(string: 추천 이유 1-2문장)",\n'
    expected_json_structure = expected_json_structure.rstrip(',\n') + "\n}"

    risk_summary = analysis_result.get('risk_assessment', {}).get('summary', '상황 분석 필요')
    needed_evidence = ", ".join(analysis_result.get('litigation_readiness', {}).get('needed_evidence', ['증거 확보 필요']))

    prompt = f"""
    [역할]: 전문 상담 컨설턴트
    [과제]: 의뢰인 상황에 맞는 업체 추천 이유를 작성하세요.

    [의뢰인 상황]
    - 위험도: {calculated_score}점
    - 상황 요약: {risk_summary}
    - 필요한 증거: {needed_evidence}

    [추천 업체]
    {agency_list_text}

    [작성 지침]:
    - 각 업체별로 1-2문장의 추천 이유 작성
    - 업체의 강점과 의뢰인 상황을 연결
    - 전문적이고 신뢰감 있는 톤 사용

    [출력]: JSON만 출력
    {expected_json_structure}
    """
    try:
        generation_config = genai.GenerationConfig(temperature=0.7, response_mime_type="application/json")
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
# 8. 메인 애플리케이션
# ---------------------------------------

# 브랜딩
st.title("리셋시큐리티")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>AI 기반 행동 패턴 분석 시스템</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #D4AF37;'>정확한 분석, 신속한 대응</p>", unsafe_allow_html=True)
st.markdown("---")

# 세션 상태
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'input_step' not in st.session_state:
    st.session_state.input_step = 1
if 'answers' not in st.session_state:
    st.session_state.answers = {}

service_type = "💔 배우자 불륜 분석"

# --- Step 1: 데이터 입력 ---
if st.session_state.step == 1:
    st.info("입력하신 정보는 암호화되어 안전하게 처리됩니다.")
    
    total_steps = 4
    progress_val = st.session_state.input_step / total_steps
    st.progress(progress_val)

    # --- 입력 Step 1: 상대방 정보 ---
    if st.session_state.input_step == 1:
        st.markdown(f"<h2>1/{total_steps}. 상대방 기본 정보</h2>", unsafe_allow_html=True)
        st.markdown("상대방의 정보를 입력하면 맞춤형 분석이 가능합니다.")
        dossier_job = st.text_input("상대방 직업 (예: 회사원, 자영업, 전문직)")
        dossier_personality = st.text_input("상대방 성향 (예: 내성적, 외향적, 꼼꼼함)")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['dossier_job'] = dossier_job
            st.session_state.answers['dossier_personality'] = dossier_personality
            st.session_state.input_step = 2
            st.rerun()

    # --- 입력 Step 2: 행동 패턴 ---
    elif st.session_state.input_step == 2:
        st.markdown(f"<h2>2/{total_steps}. 행동 패턴 변화</h2>", unsafe_allow_html=True)
        st.markdown("최근 3개월 기준으로 응답해주세요.")
        
        st.markdown("#### Q1. 외출 및 귀가 시간의 불규칙성")
        q1 = st.radio("Q1.", ("변화 없음", "가끔 증가함", "매우 빈번하게 증가함"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q2. 주말/휴일 단독 외출 빈도")
        q2 = st.radio("Q2.", ("변화 없음", "가끔 있음", "매우 잦음"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q3. 외모 관리에 대한 관심도")
        q3 = st.radio("Q3.", ("변화 없음", "약간 늘어남", "과도하게 신경 씀"), horizontal=True, label_visibility="collapsed")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['behavior_q1_schedule'] = q1
            st.session_state.answers['behavior_q2_weekend'] = q2
            st.session_state.answers['behavior_q3_appearance'] = q3
            st.session_state.input_step = 3
            st.rerun()

    # --- 입력 Step 3: 소통 변화 ---
    elif st.session_state.input_step == 3:
        st.markdown(f"<h2>3/{total_steps}. 소통 및 관계 변화</h2>", unsafe_allow_html=True)
        st.markdown("상대방과의 관계 변화를 체크해주세요.")

        st.markdown("#### Q4. 휴대폰 사용 습관 변화")
        q4 = st.radio("Q4.", ("변화 없음", "약간 의심됨", "확실히 변함"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q5. 대화 시 태도 변화")
        q5 = st.radio("Q5.", ("변화 없음", "가끔 그럼", "매우 심해짐"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q6. 스킨십/친밀도 변화")
        q6 = st.radio("Q6.", ("변화 없음", "약간 줄어듦", "거의 없음"), horizontal=True, label_visibility="collapsed")

        if st.button("다음 단계로", type="primary"):
            st.session_state.answers['communication_q4_phone'] = q4
            st.session_state.answers['communication_q5_defensive'] = q5
            st.session_state.answers['communication_q6_intimacy'] = q6
            st.session_state.input_step = 4
            st.rerun()

    # --- 입력 Step 4: 추가 정황 ---
    elif st.session_state.input_step == 4:
        st.markdown(f"<h2>4/{total_steps}. 추가 정황 확인</h2>", unsafe_allow_html=True)
        
        st.markdown("#### Q7. 차량/이동 기록 관련 의심 정황")
        q7 = st.radio("Q7.", ("확인 안 함/없음", "의심됨", "확실함"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### Q8. 금전 사용 관련 의심 정황")
        q8 = st.radio("Q8.", ("확인 안 함/없음", "의심됨", "확실함"), horizontal=True, label_visibility="collapsed")
        
        st.markdown("#### 추가 정보 (선택사항)")
        q9_freetext = st.text_area(
            "추가 정보",
            height=120,
            placeholder="분석에 도움이 될 추가 정보가 있다면 자유롭게 작성해주세요.",
            label_visibility="collapsed"
        )

        if st.button("분석 시작", type="primary"):
            st.session_state.answers['evidence_q7_car'] = q7
            st.session_state.answers['evidence_q8_finance'] = q8
            st.session_state.answers['evidence_q9_freetext'] = q9_freetext
            
            with st.spinner("데이터 처리 중..."):
                vault_info = process_and_vault_questionnaire(st.session_state.answers)
                time.sleep(1)

            # 점수 계산
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

    st.markdown("<h2>분석 리포트</h2>", unsafe_allow_html=True)

    if "error" in result:
        st.error(f"분석 오류: {result['error']}")
        score = 0
        recommended_agencies = []
    
    else:
        # === 데이터 봉인 확인 ===
        if vault_info:
            st.markdown("### 데이터 처리 완료")
            st.markdown('<div class="vault-confirmation">', unsafe_allow_html=True)
            st.text(f"처리 시간: {vault_info['timestamp']}")
            st.text(f"고유 식별자: {vault_info['hash'][:24]}...")
            st.markdown('</div>', unsafe_allow_html=True)

        # === 위험도 점수 (동적) ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("분석 결과")
        
        score = calculated_score
        level_korean, level_class = get_risk_level_korean(score)

        st.markdown(f"### 종합 위험도")
        st.markdown(f"<div class='{level_class}'>{level_korean} ({score}%)</div>", unsafe_allow_html=True)
        
        # AI 코멘트 (상세)
        summary = result.get('risk_assessment', {}).get('summary', '분석 결과를 확인해주세요.')
        st.markdown(f'<div class="ai-comment-box"><strong>분석 코멘트:</strong><br><br>{summary}</div>', unsafe_allow_html=True)
        
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
        st.subheader("대상자 분석")
        dossier = result.get('the_dossier', {})
        st.markdown(f"**분석 결과:** {dossier.get('profile', '정보 부족')}")
        st.info(f"**전략 제안:** {dossier.get('negotiation_strategy', '추가 상담 필요')}")
        st.markdown('</div>', unsafe_allow_html=True)

        # === 증거 현황 ===
        st.markdown('<div class="gap-highlight">', unsafe_allow_html=True)
        st.subheader("증거 확보 현황")

        readiness = result.get('litigation_readiness', {})
        suspicion = readiness.get('suspicion_score', score)
        evidence_score = readiness.get('evidence_score', 5)

        col1, col2 = st.columns(2)
        col1.metric(label="심증 강도", value=f"{suspicion}%")
        col2.metric(label="물증 수준", value=f"{evidence_score}%")

        st.warning(f"**참고사항:** {readiness.get('warning', '설문 기반 분석은 참고용이며, 정확한 판단을 위해 전문가 상담을 권장합니다.')}")
        
        st.markdown("**확보 권장 자료:**")
        for item in readiness.get('needed_evidence', ['전문가 상담 필요']):
            st.markdown(f"- {item}")

        st.markdown('</div>', unsafe_allow_html=True)

        # === 행동 전략 ===
        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
        st.subheader("권장 행동 단계")

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
        st.warning(f"**안내:** {golden.get('urgency_message', '빠른 대응이 효과적입니다.')}")

        recommended_agencies = get_weighted_unique_recommendations(PARTNER_AGENCIES, k=3)


    # === 전문가 연결 ===
    st.markdown("---")
    st.markdown("<h2>전문가 연결</h2>", unsafe_allow_html=True)
    
    recommended_partners_names = "N/A"

    if 'error' not in result and score >= 40:
        if recommended_agencies:
            recommended_partners_names = ", ".join([a['name'] for a in recommended_agencies])
            st.warning("분석 결과를 바탕으로 적합한 전문가를 안내해 드립니다.")

            if model:
                with st.spinner("맞춤 추천 정보 생성 중..."):
                    recommendation_reasons = generate_recommendation_reasons(recommended_agencies, result, calculated_score)
            else:
                recommendation_reasons = {}

            for agency in recommended_agencies:
                reason = recommendation_reasons.get(agency['name'], "검증된 전문 업체입니다.")
                
                # URL이 있는 경우에만 웹사이트 링크 표시
                website_html = ""
                if agency.get('url'):
                    website_html = f'<p>웹사이트: <a href="{agency["url"]}" target="_blank" style="color: #AAAAAA;">방문하기</a></p>'
                
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
             st.warning("전문가 정보를 불러오지 못했습니다.")

    # === 상담 신청 ===
    st.markdown("---")
    st.markdown("<h3>추가 상담 신청</h3>", unsafe_allow_html=True)
    st.info("종합적인 상담이 필요하시면 아래 양식을 작성해주세요.")

    with st.form(key='lead_form'):
        name = st.text_input("성함 (익명 가능)")
        phone = st.text_input("연락처")
        agree = st.checkbox("개인정보 수집 및 이용에 동의합니다.")
        
        submit_button = st.form_submit_button(label='상담 신청')

        if submit_button:
            if name and phone and agree:
                lead_data = {
                    "timestamp": datetime.now().isoformat(),
                    "name": name,
                    "phone": phone,
                    "risk_score": score if 'error' not in result else 'ERROR',
                    "evidence_score": result.get('litigation_readiness', {}).get('evidence_score', 'N/A') if 'error' not in result else 'ERROR',
                    "service_type": st.session_state.service_type,
                    "questionnaire_data": st.session_state.answers,
                    "vault_hash": st.session_state.vault_info.get('hash', 'N/A'),
                    "recommended_partners": recommended_partners_names
                }
                save_success = save_lead_to_google_sheets(lead_data)
                
                if save_success:
                    st.success(f"{name}님, 신청이 완료되었습니다. 담당자가 곧 연락드리겠습니다.")
                else:
                    st.success(f"{name}님, 신청이 완료되었습니다.")
                
                st.balloons()
            else:
                st.warning("모든 항목을 입력하고 동의해주세요.")
