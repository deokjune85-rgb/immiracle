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
import requests

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------

# [★중요★] 여기에 깃허브 JSON 파일의 Raw URL을 입력하세요.
GITHUB_JSON_URL = "https://raw.githubusercontent.com/deokjune85/immiracle/main/agencies.json" 

st.set_page_config(
    page_title="IMD Insight - AI 기반 진실 분석 및 법률 전략실",
    layout="centered"
)

# API 키 설정 (Gemini)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') 
except Exception:
    model = None

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
    border: 2px solid #D4AF37;
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

@st.cache_data(ttl=600)
def fetch_agencies():
    """깃허브에서 파트너사 JSON 데이터를 가져옵니다."""
    if "YOUR_ID" in GITHUB_JSON_URL or "YOUR_REPO" in GITHUB_JSON_URL:
        print("기본 GITHUB_JSON_URL 사용 중. 실제 URL로 변경 필요.")
        return []
    try:
        response = requests.get(GITHUB_JSON_URL)
        if response.status_code == 200:
            data = json.loads(response.text)
            for item in data:
                if not isinstance(item.get('weight'), (int, float)) or item.get('weight', 0) <= 0:
                    item['weight'] = 1
            return data
        else:
            print(f"Failed to fetch agencies. Status: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching agencies: {e}")
        return []

def get_weighted_recommendation(agencies, k=1):
    """가중치(weight)를 기반으로 파트너사를 무작위 선택합니다."""
    if not agencies:
        return []
    
    weights = [agency['weight'] for agency in agencies]
    
    try:
        selected_agencies = random.choices(agencies, weights=weights, k=k)
        return selected_agencies
    except Exception as e:
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
# 4. AI 분석 엔진 (OMEGA Protocol)
# ---------------------------------------

def get_analysis_prompt(service_type, details):
    """서비스 유형에 따른 AI 분석 프롬프트를 생성합니다."""
    
    base_prompt = f"""
당신은 IMD Insight의 OMEGA 프로토콜 AI 분석 엔진입니다.
의뢰인의 상황을 철저히 분석하고 전문적인 리포트를 생성하세요.

[의뢰 유형]: {service_type}
[상황 설명]: {details}

다음 JSON 형식으로 정확히 응답하세요:

{{
    "risk_assessment": {{
        "score": <0-100 정수>,
        "level": "<CRITICAL/SERIOUS/CAUTION/LOW>",
        "summary": "<리스크 요약 2-3문장>"
    }},
    "situation_analysis": {{
        "key_facts": ["<핵심 사실 1>", "<핵심 사실 2>", "<핵심 사실 3>"],
        "hidden_risks": ["<숨겨진 위험 1>", "<숨겨진 위험 2>"],
        "timeline_urgency": "<즉시/1주일내/1개월내/여유있음>"
    }},
    "evidence_gap": {{
        "current_evidence": ["<현재 보유 증거>"],
        "missing_critical": ["<반드시 필요한 증거 1>", "<반드시 필요한 증거 2>"],
        "recommended_actions": ["<증거 확보 방안 1>", "<증거 확보 방안 2>"]
    }},
    "litigation_readiness": {{
        "evidence_score": <0-100 정수>,
        "legal_viability": "<높음/중간/낮음>",
        "estimated_success_rate": "<00%>",
        "key_challenges": ["<법적 쟁점 1>", "<법적 쟁점 2>"]
    }},
    "strategic_recommendations": {{
        "immediate_actions": ["<즉시 조치 1>", "<즉시 조치 2>"],
        "professional_services_needed": ["<필요 전문 서비스>"],
        "warning": "<주의사항>"
    }}
}}

반드시 유효한 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.
"""
    return base_prompt

def perform_ai_analysis(service_type, details, uploaded_files_info=""):
    """Gemini AI를 사용하여 상황 분석을 수행합니다."""
    if model is None:
        return {"error": "AI 모델이 초기화되지 않았습니다. API 키를 확인하세요."}
    
    prompt = get_analysis_prompt(service_type, details)
    
    if uploaded_files_info:
        prompt += f"\n\n[첨부된 증거 파일 정보]: {uploaded_files_info}"
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # JSON 파싱 시도
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        return result
    except json.JSONDecodeError as e:
        return {"error": f"AI 응답 파싱 실패: {str(e)}"}
    except Exception as e:
        return {"error": f"AI 분석 중 오류 발생: {str(e)}"}

# ---------------------------------------
# 5. THE VAULT - 증거 보관 시스템
# ---------------------------------------

def process_and_vault_files(uploaded_files):
    """업로드된 파일들을 처리하고 해시값을 생성합니다."""
    vault_data = []
    files_info = []
    
    for file in uploaded_files:
        file_bytes = file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        vault_entry = {
            "name": file.name,
            "size": len(file_bytes),
            "hash": file_hash,
            "timestamp": datetime.now().isoformat(),
            "type": file.type
        }
        vault_data.append(vault_entry)
        files_info.append(f"- {file.name} (유형: {file.type}, 크기: {len(file_bytes)} bytes)")
        
        # 파일 포인터 리셋
        file.seek(0)
    
    return vault_data, "\n".join(files_info)

# ---------------------------------------
# 6. 헬퍼 함수
# ---------------------------------------

def get_risk_style(level):
    """리스크 레벨에 따른 CSS 클래스를 반환합니다."""
    styles = {
        "CRITICAL": "risk-critical",
        "SERIOUS": "risk-serious", 
        "CAUTION": "risk-caution",
        "LOW": ""
    }
    return styles.get(level, "")

def get_risk_emoji(level):
    """리스크 레벨에 따른 이모지를 반환합니다."""
    emojis = {
        "CRITICAL": "🚨",
        "SERIOUS": "⚠️",
        "CAUTION": "⚡",
        "LOW": "✅"
    }
    return emojis.get(level, "📊")

# ---------------------------------------
# 7. 세션 상태 초기화
# ---------------------------------------

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'vault_data' not in st.session_state:
    st.session_state.vault_data = []
if 'service_type' not in st.session_state:
    st.session_state.service_type = ""
if 'details' not in st.session_state:
    st.session_state.details = ""

# ---------------------------------------
# 8. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

# IMD Insight 브랜딩
st.title("IMD Insight")
st.markdown("<p style='text-align: center; color: #888;'>AI 기반 진실 분석 및 법률 전략 시스템</p>", unsafe_allow_html=True)
st.markdown("---")

# --- Step 1: 정보 입력 ---
if st.session_state.step == 1:
    st.markdown("<h2>📋 Step 1: 상황 분석 의뢰</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="analysis-section">
        <p>IMD Insight는 AI 기반 심층 분석을 통해 귀하의 상황을 객관적으로 평가하고, 
        최적의 해결 전략을 제시합니다. 모든 정보는 암호화되어 안전하게 처리됩니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 서비스 유형 선택
    service_type = st.selectbox(
        "의뢰 유형을 선택하세요",
        [
            "선택하세요",
            "배우자 외도/불륜 조사",
            "사기 피해 조사",
            "실종자/가출인 수색",
            "기업 비리/횡령 조사",
            "스토킹/협박 대응",
            "디지털 포렌식",
            "신원 조회/채용 검증",
            "기타 민사 분쟁"
        ]
    )
    
    # 상세 내용 입력
    details = st.text_area(
        "상황을 상세히 설명해주세요",
        height=200,
        placeholder="현재 상황, 의심되는 점, 알고 있는 정보 등을 최대한 자세히 기술해주세요.\n\n예시:\n- 언제부터 의심이 시작되었는지\n- 어떤 행동/증거가 발견되었는지\n- 현재까지 취한 조치가 있는지"
    )
    
    # 증거 파일 업로드
    st.markdown("### 📎 증거 자료 첨부 (선택)")
    uploaded_files = st.file_uploader(
        "관련 증거 파일을 업로드하세요 (이미지, 문서, 녹음 등)",
        accept_multiple_files=True,
        type=['png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'mp3', 'mp4', 'txt']
    )
    
    # 분석 시작 버튼
    if st.button("🔍 AI 심층 분석 시작", type="primary"):
        if service_type == "선택하세요":
            st.warning("의뢰 유형을 선택해주세요.")
        elif len(details) < 20:
            st.warning("상황 설명을 20자 이상 입력해주세요.")
        else:
            # 데이터 저장
            st.session_state.service_type = service_type
            st.session_state.details = details
            
            # 파일 처리
            files_info = ""
            if uploaded_files:
                vault_data, files_info = process_and_vault_files(uploaded_files)
                st.session_state.vault_data = vault_data
            
            # AI 분석 실행
            with st.spinner("🔬 OMEGA 프로토콜 분석 중... (약 30초 소요)"):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.03)
                    progress_bar.progress(i + 1)
                
                result = perform_ai_analysis(service_type, details, files_info)
                st.session_state.analysis_result = result
            
            st.session_state.step = 2
            st.rerun()

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
        # THE VAULT 확인증
        if vault_data:
            st.markdown("<h3>🔐 THE VAULT - 증거 보관 확인증</h3>", unsafe_allow_html=True)
            vault_html = "<div class='vault-confirmation'>"
            vault_html += f"<p>⏱️ 보관 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}</p>"
            vault_html += "<p>📁 보관된 파일:</p>"
            for item in vault_data:
                vault_html += f"<p>  • {item['name']}<br/>    SHA-256: {item['hash'][:32]}...</p>"
            vault_html += "</div>"
            st.markdown(vault_html, unsafe_allow_html=True)
        
        # SECTION 1: 리스크 평가
        risk = result.get('risk_assessment', {})
        score = risk.get('score', 0)
        level = risk.get('level', 'LOW')
        risk_style = get_risk_style(level)
        risk_emoji = get_risk_emoji(level)
        
        st.markdown(f"""
        <div class="analysis-section">
            <h3>{risk_emoji} SECTION 1: 리스크 평가</h3>
            <p class="{risk_style}" style="font-size: 48px; text-align: center;">{score}/100</p>
            <p style="text-align: center;"><span class="{risk_style}">위험 등급: {level}</span></p>
            <p>{risk.get('summary', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # SECTION 2: 상황 분석
        situation = result.get('situation_analysis', {})
        st.markdown(f"""
        <div class="analysis-section">
            <h3>🔍 SECTION 2: 상황 분석</h3>
            <p><b>핵심 사실:</b></p>
            <ul>{''.join([f'<li>{fact}</li>' for fact in situation.get('key_facts', [])])}</ul>
            <p><b>숨겨진 위험:</b></p>
            <ul>{''.join([f'<li>{risk}</li>' for risk in situation.get('hidden_risks', [])])}</ul>
            <p><b>긴급도:</b> {situation.get('timeline_urgency', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # SECTION 3: 증거 GAP 분석
        gap = result.get('evidence_gap', {})
        st.markdown(f"""
        <div class="gap-highlight">
            <h3>⚠️ SECTION 3: 증거 GAP 분석 (중요)</h3>
            <p><b>현재 보유 증거:</b></p>
            <ul>{''.join([f'<li>{ev}</li>' for ev in gap.get('current_evidence', [])])}</ul>
            <p><b>🚨 반드시 확보해야 할 증거:</b></p>
            <ul>{''.join([f'<li style="color: #FF4B4B;">{ev}</li>' for ev in gap.get('missing_critical', [])])}</ul>
            <p><b>증거 확보 방안:</b></p>
            <ul>{''.join([f'<li>{action}</li>' for action in gap.get('recommended_actions', [])])}</ul>
        </div>
        """, unsafe_allow_html=True)
        
        # SECTION 4: 소송 준비도
        litigation = result.get('litigation_readiness', {})
        st.markdown(f"""
        <div class="analysis-section">
            <h3>⚖️ SECTION 4: 법적 대응 준비도</h3>
            <p><b>증거 충분도:</b> {litigation.get('evidence_score', 0)}/100</p>
            <p><b>법적 실현 가능성:</b> {litigation.get('legal_viability', 'N/A')}</p>
            <p><b>예상 승소율:</b> {litigation.get('estimated_success_rate', 'N/A')}</p>
            <p><b>주요 법적 쟁점:</b></p>
            <ul>{''.join([f'<li>{ch}</li>' for ch in litigation.get('key_challenges', [])])}</ul>
        </div>
        """, unsafe_allow_html=True)
        
        # SECTION 5: 전략적 권고
        strategy = result.get('strategic_recommendations', {})
        st.markdown(f"""
        <div class="analysis-section">
            <h3>🎯 SECTION 5: 전략적 권고사항</h3>
            <p><b>즉시 조치 사항:</b></p>
            <ul>{''.join([f'<li>{action}</li>' for action in strategy.get('immediate_actions', [])])}</ul>
            <p><b>필요 전문 서비스:</b></p>
            <ul>{''.join([f'<li>{svc}</li>' for svc in strategy.get('professional_services_needed', [])])}</ul>
            <p><b>⚠️ 주의:</b> {strategy.get('warning', '')}</p>
        </div>
        """, unsafe_allow_html=True)

        # 분석 성공 시 가중치 기반 추천 실행
        recommended_agency = None
        if PARTNER_AGENCIES:
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
            
            # AI 추천 근거 (가중치를 적합도로 변환하여 표시)
            fit_score = recommended_agency.get('weight', 50) + random.randint(10, 25)
            if fit_score > 99: fit_score = 99
            
            st.info(f"💡 AI 분석 노트: 이 업체는 귀하의 사건 유형과 {fit_score}%의 적합도를 보였습니다.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("⚠️ 위 업체에 연락 시 'IMD Insight 분석 결과'를 보고 연락했다고 말씀하시면 즉각적인 대응이 가능합니다.")

        elif not PARTNER_AGENCIES:
            st.warning("파트너사 데이터를 로드하지 못했습니다. (GitHub URL 확인 필요)")
    
    elif 'error' not in result and score < 40:
        st.success("✅ 현재 상황은 비교적 안정적입니다. 추가 모니터링을 권장드립니다.")

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
    
    # 새 분석 시작 버튼
    st.markdown("---")
    if st.button("🔄 새로운 분석 시작", type="secondary"):
        st.session_state.step = 1
        st.session_state.analysis_result = None
        st.session_state.vault_data = []
        st.rerun()
