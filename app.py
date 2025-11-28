import streamlit as st
import google.generativeai as genai
import time
import io
from PIL import Image
import json
import random
import requests

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------
st.set_page_config(
    page_title="IMD Insight - Private Intelligence",
    page_icon="👁️",
    layout="centered"
)

# API 키 설정 (Streamlit Secrets 사용)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') 
except Exception as e:
    st.error(f"❌ 보안 시스템 초기화 실패: API KEY 확인 필요. {e}")
    st.stop()

# ---------------------------------------
# 1. UI/UX 스타일링 (Premium Dark + Omega Protocol)
# ---------------------------------------
custom_css = """
<style>
/* === 스텔스 모드 === */
#MainMenu { visibility: hidden !important; } 
header { visibility: hidden !important; }    
footer { visibility: hidden !important; }    
.stDeployButton { display: none !important; }
[data-testid="stSidebar"] { display: none; }

/* === 디자인 테마 === */
.stApp { background-color: #0E0E0E; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
h1, h2, h3 { color: #D4AF37; font-family: serif; font-weight: 800; }
.stButton>button { background-color: #D4AF37 !important; color: #000 !important; font-weight: bold; border: none; }

/* === 커스텀 컴포넌트 === */
.analysis-card { background-color: #1A1A1A; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
.villain-card { background: linear-gradient(135deg, #2C2C2C 0%, #1A1A1A 100%); border-left: 5px solid #FF4B4B; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
.finance-box { background-color: #112211; border: 2px solid #00FF00; padding: 20px; border-radius: 10px; text-align: center; font-family: 'Courier New', monospace; color: #00FF00; margin-bottom: 20px; }
.gap-box { background-color: #2D0F0F; border: 2px solid #FF4B4B; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
.highlight { color: #D4AF37; font-weight: bold; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. 데이터 & AI 엔진
# ---------------------------------------

# 깃허브 JSON 데이터 로드 (가중치 추천용)
@st.cache_data(ttl=300)
def fetch_agencies():
    url = "https://raw.githubusercontent.com/deokjune85-rgb/immiracle/main/agencies.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return json.loads(response.text)
        return []
    except:
        return []

def get_weighted_agency(agencies):
    if not agencies: return None
    weights = [agency.get('weight', 10) for agency in agencies]
    return random.choices(agencies, weights=weights, k=1)[0]

def get_analysis_prompt(details):
    # OMEGA Protocol JSON Schema v4.0 (확장판)
    schema = """
    {
      "risk": { "score": (int: 0-100), "level": "(CRITICAL/SERIOUS/CAUTION)" },
      "villain_profile": {
        "type": "(string: 예: 가스라이팅형 나르시시스트, 회피형 쫄보, 쾌락형 소시오패스 중 택1)",
        "desc": "(string: 해당 유형의 행동 특징 1줄 요약)",
        "weakness": "(string: 이 유형을 무너뜨리는 법적/심리적 약점)"
      },
      "financial_forecast": {
        "alimony": "(string: 예상 위자료, 예: 3,000만원)",
        "division": "(string: 예상 재산분할 비율, 예: 40~50%)",
        "total_gain": "(string: 총 예상 확보 금액, 예: 2억 5천만원)"
      },
      "deep_analysis": {
        "alibi_crack": "(string: 알리바이 모순점 분석)",
        "behavior_flag": "(string: 행동 심리 분석)"
      },
      "litigation_readiness": {
        "suspicion": (int: 심증 점수, risk.score와 동일),
        "evidence": (int: 물증 점수, 0-30점으로 매우 짜게 줄것),
        "warning": "(string: 증거 부족에 대한 강력한 경고)"
      },
      "simulation": {
        "scenario": "(string: 남편의 핸드폰이 책상 위에 놓여있는 상황 등)",
        "choice_bad": "(string: 감정적 대응 예시)",
        "result_bad": "(string: 실패 결과)",
        "choice_good": "(string: 냉정한 대응 예시)",
        "result_good": "(string: 성공 결과)"
      },
      "golden_time": { "days_left": (int: 2-7일 랜덤) }
    }
    """
    return f"""
    [역할]: 당신은 냉철한 AI 탐정이자 법률 전략가입니다.
    [목표]: 사용자의 정황을 분석하여 외도 가능성을 진단하고, 심리적/금전적 대응 전략을 수립합니다.
    [지침]:
    1. 'villain_profile'은 MBTI나 행동 패턴을 기반으로 빌런 유형을 정의하십시오.
    2. 'financial_forecast'는 사용자의 분노를 '돈'으로 치환하여 보여주십시오.
    3. 'litigation_readiness.evidence'는 매우 낮게 책정하여(30점 이하) 전문가의 도움이 절실함을 강조하십시오.
    
    [입력 데이터]: {details}
    [출력 형식]: JSON 포맷 준수.
    {schema}
    """

def perform_ai_analysis(details, files):
    prompt = get_analysis_prompt(details)
    payload = [prompt]
    
    # 파일 처리 (이미지/텍스트)
    if files:
        for file in files:
            try:
                if file.type.startswith("image/"):
                    img = Image.open(file)
                    img_byte_arr = io.BytesIO()
                    img.convert('RGB').save(img_byte_arr, format='JPEG')
                    payload.append({"mime_type": "image/jpeg", "data": img_byte_arr.getvalue()})
                elif "text" in file.type:
                    payload.append(f"\n[파일 내용]: {file.getvalue().decode('utf-8', errors='ignore')[:1000]}\n")
            except: pass

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        res = model.generate_content(payload, generation_config={"response_mime_type": "application/json"})
        return json.loads(res.text)
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------
# 3. 메인 앱 로직
# ---------------------------------------

if 'step' not in st.session_state:
    st.session_state.step = 1

# [STEP 1] 입력 화면
if st.session_state.step == 1:
    st.image("https://images.unsplash.com/photo-1555431189-0fabf2667795?q=80&w=1000&auto=format&fit=crop", use_column_width=True)
    st.title("IMD Insight : The Truth")
    st.markdown("### 당신의 '의심'을 '확신'과 '증거'로 바꿔드립니다.")
    
    with st.container(border=True):
        st.subheader("🕵️‍♂️ 사건 정황 입력")
        details = st.text_area("구체적인 상황을 입력하세요 (MBTI를 적으면 더 정확해집니다)", height=150, placeholder="예: 남편(ENTJ)이 요즘 야근이 잦고, 차에서 낯선 영수증이 나왔습니다.")
        files = st.file_uploader("증거 자료 (카톡 캡처, 카드 내역)", accept_multiple_files=True)
        
        if st.button("⚡ AI 정밀 분석 시작 (무료)", type="primary"):
            if not details:
                st.toast("정황을 입력해주세요.")
            else:
                with st.spinner("AI 프로파일러가 데이터를 분석 중입니다..."):
                    res = perform_ai_analysis(details, files)
                    st.session_state.result = res
                    st.session_state.step = 2
                    st.rerun()

# [STEP 2] 결과 리포트
elif st.session_state.step == 2:
    res = st.session_state.result
    
    if "error" in res:
        st.error("분석 중 오류가 발생했습니다. 다시 시도해주세요.")
        if st.button("뒤로가기"): st.session_state.step = 1; st.rerun()
    else:
        # 1. 헤더 (점수)
        st.markdown(f"<h1 style='text-align: center; color: #FF4B4B;'>위험도 {res['risk']['score']}% ({res['risk']['level']})</h1>", unsafe_allow_html=True)
        st.progress(res['risk']['score'] / 100)
        
        # 2. 빌런 프로파일링 (재미 요소)
        villain = res['villain_profile']
        st.markdown(f"""
        <div class="villain-card">
            <h3>🃏 배우자 유형: {villain['type']}</h3>
            <p><strong>특징:</strong> {villain['desc']}</p>
            <p><strong>⚠️ 약점:</strong> {villain['weakness']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. 금융 치료 계산기 (탐욕 자극)
        finance = res['financial_forecast']
        st.markdown(f"""
        <div class="finance-box">
            <h3>💸 금융 치료 견적서 (예상)</h3>
            <p>위자료: {finance['alimony']} | 재산분할: {finance['division']}</p>
            <h2 style='color: #00FF00; margin: 0;'>TOTAL: {finance['total_gain']}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # 4. 법적 준비도 (공포 자극)
        gap = res['litigation_readiness']
        st.markdown(f"""
        <div class="gap-box">
            <h3>⚖️ 소송 준비도 진단</h3>
            <p>심증(의심): <span class="highlight">{gap['suspicion']}%</span> vs 물증(효력): <span style='color: #FF4B4B;'>{gap['evidence']}%</span></p>
            <p>{gap['warning']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 5. VS 시뮬레이션 (몰입 유도)
        sim = res['simulation']
        with st.expander("🎮 [VS] 당신의 선택에 따른 결말 시뮬레이션", expanded=True):
            st.write(f"**상황:** {sim['scenario']}")
            c1, c2 = st.columns(2)
            with c1:
                st.error(f"❌ [감정적 대응]\n{sim['choice_bad']}")
                st.caption(f"결과: {sim['result_bad']}")
            with c2:
                st.success(f"✅ [냉정한 대응]\n{sim['choice_good']}")
                st.caption(f"결과: {sim['result_good']}")
                
        # 6. 골든타임 & 전문가 매칭 (해결책)
        st.markdown("---")
        st.subheader("⏳ 골든타임 경고")
        st.warning(f"증거(CCTV/블랙박스) 삭제까지 약 {res['golden_time']['days_left']}일 남았습니다.")
        
        st.markdown("### 💡 IMD 공식 인증 파트너 추천")
        st.info("AI가 귀하의 상황을 해결할 최적의 전문가를 매칭했습니다.")
        
        # 깃허브에서 가져온 업체 데이터 가중치 추천
        agencies = fetch_agencies()
        target = get_weighted_agency(agencies)
        
        if target:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"### 🏆 {target['name']}")
                    st.write(target['desc'])
                    st.write(f"📞 **{target['phone']}**")
                with c2:
                    st.link_button("상담 연결", target['url'], type="primary")
        
        if st.button("다시 분석하기"):
            st.session_state.step = 1
            st.rerun()
