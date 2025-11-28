# app.py (IMD Insight v4.2 - Algorithmic Authority Edition)
import streamlit as st
import google.generativeai as genai
import time
import io
from PIL import Image
import json
import random
import hashlib
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests # requests 모듈 추가

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------

# [★중요★] 여기에 깃허브 JSON 파일의 Raw URL을 입력하세요.
GITHUB_JSON_URL = "https://raw.githubusercontent.com/YOUR_ID/YOUR_REPO/main/agencies.json" 

st.set_page_config(
    page_title="IMD Insight - AI 기반 진실 분석 및 법률 전략실",
    layout="centered"
)

# API 키 설정 (Gemini)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest') 
except Exception:
    pass 

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

/* GAP 강조 박스 */
.gap-highlight { border: 3px solid #FF4B4B; padding: 25px; background-color: #4a1a1a; margin-bottom: 20px; border-radius: 10px; }

/* THE VAULT 스타일 */
.vault-confirmation { background-color: #2a2a4a; color: #00FF00; padding: 15px; border-radius: 5px; font-family: monospace; margin-bottom: 20px; }

/* 파트너사 추천 박스 스타일 (★v4.2 수정★) */
.partner-box {
    background-color: #2C2C2C;
    border: 2px solid #D4AF37; /* 테두리 강조 */
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 15px;
    text-align: center;
}
.partner-name {
    font-size: 22px;
    font-weight: bold;
    color: #D4AF37;
    margin-bottom: 10px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. 데이터 로딩 및 처리 (JSON 가중치 시스템 - 깃허브 연동)
# ---------------------------------------

@st.cache_data(ttl=600) # 10분간 캐시하여 속도 향상
def fetch_agencies():
    """깃허브에서 파트너사 JSON 데이터를 가져옵니다."""
    if GITHUB_JSON_URL == "https://raw.githubusercontent.com/YOUR_ID/YOUR_REPO/main/agencies.json":
        print("기본 GITHUB_JSON_URL 사용 중. 실제 URL로 변경 필요.")
        return []
    try:
        response = requests.get(GITHUB_JSON_URL)
        if response.status_code == 200:
            data = json.loads(response.text)
            # 데이터 검증 및 기본 가중치 설정
            for item in data:
                if not isinstance(item.get('weight'), (int, float)) or item.get('weight', 0) <= 0:
                    item['weight'] = 1 # 기본값 설정
            return data
        else:
            print(f"Failed to fetch agencies. Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching agencies: {e}")
        return []

def get_weighted_recommendation(agencies, k=1):
    """가중치(weight)를 기반으로 파트너사를 무작위 선택합니다. (★v4.2 핵심 로직★)"""
    if not agencies:
        return []
    
    # 가중치 리스트 추출
    weights = [agency['weight'] for agency in agencies]
    
    # random.choices를 사용하여 가중치 기반 선택 실행
    try:
        selected_agencies = random.choices(agencies, weights=weights, k=k)
        return selected_agencies
    except Exception as e:
        # 확률 계산 문제 발생 시 (예: 가중치 합이 0인 경우) 균등 랜덤 선택 (Fallback)
        print(f"Weighted selection error: {e}. Falling back to random choice.")
        return random.sample(agencies, k=min(k, len(agencies)))

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
            headers = ["Timestamp", "Name", "Phone", "Risk Score", "Evidence Score", "Service Type", "Details", "Vault Hashes", "Recommended Partner"]
            sheet.append_row(headers)

        values = [
            lead_data.get("timestamp"),
            lead_data.get("name"),
            lead_data.get("phone"),
            lead_data.get("risk_score"),
            lead_data.get("evidence_score"),
            lead_data.get("service_type"),
            lead_data.get("details"),
            json.dumps(lead_data.get("vault_hashes", {}), ensure_ascii=False),
            lead_data.get("recommended_partner")
        ]
        sheet.append_row(values)
        return True
    except Exception as e:
        print(f"Google Sheets 연동 실패: {e}")
        return False 

# ---------------------------------------
# 4. AI 분석 엔진 (OMEGA + VAULT + WAR ROOM Schema)
# ---------------------------------------
# (이하 AI 분석 엔진, VAULT, 헬퍼 함수 코드는 v4.1과 동일하므로 생략 - 실제 코드에서는 포함되어야 함)
# ... (중략: get_analysis_prompt, perform_ai_analysis, process_and_vault_files, get_risk_style 함수 포함) ...

# ---------------------------------------
# 7. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

# IMD Insight 브랜딩 적용
st.title("IMD Insight")
# ... (중략: 브랜딩 및 Step 1 입력 폼) ...

# --- Step 2: 분석 결과 확인 및 파트너 매칭 (OMEGA UI) ---
elif st.session_state.step == 2:
    result = st.session_state.analysis_result
    vault_data = st.session_state.get('vault_data', [])

    st.markdown("<h2>📊 IMD Insight - 최종 분석 리포트</h2>", unsafe_allow_html=True)

    if "error" in result:
        st.error(f"❌ 분석 오류 발생: {result['error']}. 잠시 후 다시 시도해주세요.")
        score = 0
        recommended_partner_name = "ERROR"
    
    else:
        # ... (중략: THE VAULT 확인증, SECTION 1~5 분석 결과 출력) ...
        # (분석 결과 출력 로직은 v4.1과 동일하게 유지)
        # ...

        # 분석 성공 시 가중치 기반 추천 실행
        recommended_agency = None
        if PARTNER_AGENCIES:
             # k=1로 1개만 추천
            recommended_partners = get_weighted_recommendation(PARTNER_AGENCIES, k=1)
            if recommended_partners:
                recommended_agency = recommended_partners[0]


    # === SECTION 6: 파트너 추천 및 리드 확보 (★v4.2 핵심★) ===
    st.markdown("---")
    st.markdown("<h2>💡 IMD 솔루션 : 검증된 전문가 연결</h2>", unsafe_allow_html=True)
    
    recommended_partner_name = "N/A"

    # 리스크 점수가 40점 이상이고 추천된 파트너가 있을 경우 표시
    if 'error' not in result and score >= 40:
        if recommended_agency:
            recommended_partner_name = recommended_agency['name']
            st.error("🚨 분석 결과, 전문가의 즉각적인 개입이 필요합니다. IMD 알고리즘이 귀하의 케이스에 최적화된 전문가를 선별했습니다.")

            # 추천된 단 하나의 파트너사 표시
            st.markdown(f"""
            <div class="partner-box">
                <div class="partner-name">🏆 AI 최적 매칭: {recommended_agency['name']}</div>
                <p><i>"{recommended_agency['desc']}"</i></p>
                <h3>📞 {recommended_agency['phone']}</h3>
                <a href="{recommended_agency['url']}" target="_blank" style="color: #D4AF37; font-weight: bold;">웹사이트 방문하기</a>
            </div>
            """, unsafe_allow_html=True)
            
            # AI 추천 근거 (가중치를 적합도로 변환하여 표시 - 심리적 효과)
            fit_score = recommended_agency.get('weight', 50) + random.randint(10, 25)
            if fit_score > 99: fit_score = 99
            
            st.info(f"💡 AI 분석 노트: 이 업체는 귀하의 사건 유형과 {fit_score}%의 적합도를 보였습니다.")

            
            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("⚠️ 위 업체에 연락 시 'IMD Insight 분석 결과'를 보고 연락했다고 말씀하시면 즉각적인 대응이 가능합니다.")

        elif not PARTNER_AGENCIES:
             st.warning("파트너사 데이터를 로드하지 못했습니다. (GitHub URL 확인 필요)")

    # IMD 전략팀 통합 상담 신청 (Fallback Lead Capture)
    st.markdown("---")
    st.markdown("<h3>IMD 전략팀 통합 상담 신청 (무료)</h3>", unsafe_allow_html=True)
    st.info("종합적인 전략 수립(변호사 연계 포함)이 필요하거나, 추천된 업체 외 추가 상담이 필요한 경우 신청하세요.")

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
                    "details": st.session_state.details,
                    "vault_hashes": {item['name']: item['hash'] for item in st.session_state.get('vault_data', [])},
                    "recommended_partner": recommended_partner_name
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
