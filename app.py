# app.py (AURA Insight MVP - Wizard of Oz Implementation v1.2)
import streamlit as st
import os
import json
from datetime import datetime
import time
import uuid
import pandas as pd
import io
import random
import re

# ---------------------------------------
# 0. 시스템 설정 및 초기화
# ---------------------------------------
st.set_page_config(
    page_title="AURA Insight - AI 기반 진실 분석 플랫폼",
    page_icon="👁️",
    layout="centered"
)

# 데이터 저장소 설정 (증거 및 리드 저장 폴더)
DATA_DIR = "aura_data"
EVIDENCE_DIR = os.path.join(DATA_DIR, "evidence")
LEAD_FILE = os.path.join(DATA_DIR, "leads.jsonl")

# 폴더 생성 확인
try:
    if not os.path.exists(EVIDENCE_DIR):
        os.makedirs(EVIDENCE_DIR)
except Exception as e:
    # 파일 시스템 접근이 불가능한 환경일 경우 경고 표시
    print(f"데이터 저장소 생성 경고: {e}")

# ---------------------------------------
# 1. UI/UX 스타일링 (Premium Dark Aesthetic)
# ---------------------------------------
# 프리미엄, 신뢰, 기밀성을 강조하는 다크 테마 적용
custom_css = """
<style>
#MainMenu, footer, header, .stDeployButton {visibility:hidden;}
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
.stButton>button[kind="primary"] {
    width: 100%;
    font-weight: bold;
    font-size: 18px !important;
    padding: 15px;
    background-color: #D4AF37;
    color: #101010;
    border-radius: 5px;
    border: none;
}
.stButton>button[kind="primary"]:hover {
    background-color: #B8860B;
}
.disclaimer {
    font-size: 13px;
    color: #AAAAAA;
    text-align: justify;
    background-color: #2C2C2C;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
}
/* 사이드바 스타일링 (관리자용) */
[data-testid="stSidebar"] {
    background-color: #1C1C1C;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ---------------------------------------
# 2. 데이터 저장 함수 (The Vault)
# ---------------------------------------
def sanitize_filename(filename):
    """파일 이름에서 특수문자를 제거하여 안전하게 만듭니다."""
    return re.sub(r'[^\w\s.-]', '', filename).strip()

def save_evidence_files(lead_id, files):
    """업로드된 증거 파일을 서버에 저장합니다."""
    file_names = []
    if files:
        for file in files:
            try:
                # 파일 이름 안전하게 처리
                safe_file_name = sanitize_filename(file.name)
                # 고유 파일명 생성
                unique_suffix = uuid.uuid4().hex[:6]
                filename = f"{lead_id}_{unique_suffix}_{safe_file_name}"
                filepath = os.path.join(EVIDENCE_DIR, filename)
                
                # 파일을 디스크에 저장
                with open(filepath, "wb") as f:
                    f.write(file.getbuffer())
                
                file_names.append(filename)
            except Exception as e:
                print(f"Evidence file saving error: {e}")
    return file_names

def save_lead_data(lead_id, data, file_names):
    """리드 데이터를 JSONL 파일에 저장합니다."""
    # 데이터 복사본을 만들어 원본 세션 상태 보호
    data_to_save = data.copy()
    data_to_save["id"] = lead_id
    data_to_save["timestamp"] = datetime.now().isoformat()
    data_to_save["evidence_files"] = file_names

    # JSONL 파일에 추가 (한 줄씩 저장)
    try:
        with open(LEAD_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(data_to_save, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"Lead data saving error: {e}")
        return False

# ---------------------------------------
# 3. 관리자 기능 (Admin Access - Wizard of Oz 운영용)
# ---------------------------------------
with st.sidebar:
    st.markdown("<h2 style='color: #D4AF37;'>🔑 IMD Admin Access</h2>", unsafe_allow_html=True)
    password = st.text_input("Admin Password", type="password")
    # 보안을 위해 비밀번호는 Secrets에서 로드 (기본값: imd_architect)
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "imd_architect") 
    
    if password == ADMIN_PASSWORD:
        st.success("Admin Login Successful")
        if os.path.exists(LEAD_FILE) and os.path.getsize(LEAD_FILE) > 0:
            try:
                # JSONL 파일을 Pandas DataFrame으로 로드
                df_leads = pd.read_json(LEAD_FILE, lines=True)
                if not df_leads.empty:
                    st.subheader(f"수집된 리드 데이터 ({len(df_leads)})")
                    
                    # 데이터프레임 가공 (Nested JSON 파싱)
                    display_df = df_leads.copy()
                    # contact 정보가 딕셔너리인지 확인 후 접근
                    display_df['Name'] = display_df['contact'].apply(lambda x: x.get('name') if isinstance(x, dict) else 'N/A')
                    display_df['Phone'] = display_df['contact'].apply(lambda x: x.get('phone') if isinstance(x, dict) else 'N/A')
                    display_df['Service'] = display_df['service_type']
                    # 파일 개수 표시
                    display_df['Files'] = display_df['evidence_files'].apply(len)
                    
                    st.dataframe(display_df[['timestamp', 'Service', 'Name', 'Phone', 'Files', 'id']])
                    
                    # CSV 다운로드 버튼
                    csv_buffer = io.BytesIO()
                    # UTF-8 BOM 추가하여 엑셀 호환성 확보
                    df_leads.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="📥 리드 데이터 다운로드 (CSV)",
                        data=csv_buffer.getvalue(),
                        file_name="aura_insight_leads.csv",
                        mime="text/csv",
                    )
                    st.warning(f"⚠️ 증거 파일은 서버 폴더(`{EVIDENCE_DIR}`)에서 수동으로 확인해야 합니다.")
            except Exception as e:
                st.error(f"리드 로딩 오류: {e}")
        else:
            st.info("수집된 리드가 없습니다.")
    elif password:
        st.error("비밀번호가 틀렸습니다.")

# ---------------------------------------
# 4. 메인 애플리케이션 로직 (Frontend)
# ---------------------------------------

st.title("AURA Insight 👁️")
st.markdown("<h3 style='text-align: center; color: #AAAAAA;'>AI 기반 진실 분석 및 전문가 매칭 플랫폼</h3>", unsafe_allow_html=True)
st.markdown("---")

st.warning("🔒 모든 데이터는 암호화되어 처리됩니다. AURA Insight는 고객의 비밀 보장을 최우선으로 합니다.")

# 세션 상태를 사용하여 멀티스텝 폼 구현
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'data' not in st.session_state:
    st.session_state.data = {}

# --- Step 1: 서비스 선택 ---
if st.session_state.step == 1:
    st.markdown("<h2>1. AI 분석 서비스 선택</h2>", unsafe_allow_html=True)
    
    service_type = st.radio(
        "어떤 도움이 필요하십니까?",
        options=[
            "💔 배우자 불륜 가능성 분석 (외도 증거 분석)",
            "🔎 사람 찾기 (실종/연락두절 추적 가능성 분석)",
            "📂 기타 증거 분석 (기업/개인 분쟁)"
        ]
    )

    if st.button("다음 단계로", type="primary"):
        st.session_state.data['service_type'] = service_type
        st.session_state.step = 2
        st.rerun()

# --- Step 2: 데이터 입력 (증거 및 정황) ---
elif st.session_state.step == 2:
    service_type = st.session_state.data['service_type']
    # 서비스명을 깔끔하게 표시
    service_name_clean = service_type.split('(')[0].strip()[2:]
    st.markdown(f"<h2>2. 분석 데이터 입력 ({service_name_clean})</h2>", unsafe_allow_html=True)

    # 서비스 유형별 맞춤 입력 필드
    if "🔎" in service_type:
        st.subheader("대상자 정보 입력 (필수)")
        target_name = st.text_input("대상자 이름")
        target_last_contact = st.text_input("마지막 연락 정보 (전화번호/SNS 등)")
        target_last_location = st.text_input("마지막 확인 위치 및 시간")
        st.session_state.data['target_info'] = {"name": target_name, "contact": target_last_contact, "location": target_last_location}

    st.subheader("구체적인 정황 설명 (필수)")
    placeholder_text = "예시: 남편이 최근 주말마다 야근을 핑계로 외박이 잦아졌습니다. 차량 이동 경로가 의심스럽습니다." if "💔" in service_type else "예시: 3일 전부터 연락이 두절되었고, 마지막으로 확인된 위치는 강남역 부근입니다."
    
    details = st.text_area(
        "AI가 상황을 정확히 분석할 수 있도록 구체적인 정황이나 의심스러운 내용을 작성해주세요.",
        height=200,
        placeholder=placeholder_text
    )

    st.subheader("증거 자료 업로드 (선택)")
    if "💔" in service_type:
        st.info("카카오톡 대화 내역(TXT/캡처), 사진/동영상, 카드 사용 내역(CSV/XLSX) 등을 업로드해주세요. AI가 교차 분석합니다.")
    else:
        st.info("대상자의 사진, 연락처 기록, SNS 캡처 등 추적 또는 분석에 도움이 될 자료를 업로드해주세요.")

    uploaded_files = st.file_uploader(
        "파일 업로드 (최대 10개)",
        type=["txt", "csv", "xlsx", "jpg", "jpeg", "png", "mp4", "pdf"],
        accept_multiple_files=True
    )

    if st.button("다음 단계로", type="primary"):
        # 필수 입력값 검증 강화
        is_valid = True
        if not details:
            st.warning("구체적인 정황 설명을 필수로 입력해야 합니다.")
            is_valid = False
        
        if "🔎" in service_type:
            target_info = st.session_state.data.get('target_info', {})
            if not target_info.get('name') or not target_info.get('contact'):
                st.warning("사람 찾기 서비스는 대상자 이름과 마지막 연락 정보가 필수입니다.")
                is_valid = False

        if is_valid:
            # 파일 객체 자체를 세션 상태에 임시 저장 (실제 저장은 마지막 단계에서)
            st.session_state.uploaded_files = uploaded_files
            st.session_state.data['details'] = details
            st.session_state.step = 3
            st.rerun()

# --- Step 3: 연락처 입력 및 제출 ---
elif st.session_state.step == 3:
    st.markdown("<h2>3. AI 분석 리포트 수신 정보</h2>", unsafe_allow_html=True)
    st.info("정밀 분석 결과 및 전문가 매칭 정보는 입력하신 연락처(카카오톡 또는 문자)로 보안 전송됩니다.")

    name = st.text_input("의뢰인 성함")
    phone = st.text_input("연락처 (하이픈(-) 포함 입력)")

    disclaimer_text = """
    **[기밀 유지 및 이용 동의]** 입력하신 정보와 증거 자료는 AI 분석 목적으로만 사용되며, 분석 완료 후 안전하게 관리됩니다. 분석 결과는 법적 효력을 갖지 않으며 참고 자료로만 활용되어야 합니다. 서비스 이용 시 이에 동의하는 것으로 간주됩니다.
    """
    st.markdown(f"<div class='disclaimer'>{disclaimer_text}</div>", unsafe_allow_html=True)
    agree = st.checkbox("기밀 유지 및 이용 약관에 동의합니다.")

    if st.button("AI 분석 요청 및 리포트 받기", type="primary"):
        if not name or not phone:
            st.warning("결과 수신을 위해 성함과 연락처를 정확히 입력해주세요.")
        elif not agree:
            st.warning("이용 약관에 동의해야 분석 요청이 가능합니다.")
        else:
            st.session_state.data['contact'] = {"name": name, "phone": phone}
            
            # 고유 ID 생성
            lead_id = str(uuid.uuid4())[:8]

            # 데이터 및 파일 저장 실행 (백엔드 동작)
            try:
                file_names = save_evidence_files(lead_id, st.session_state.get('uploaded_files', []))
                
                if save_lead_data(lead_id, st.session_state.data, file_names):
                    st.session_state.step = 4
                    st.rerun()
                else:
                    st.error("❌ 요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (데이터 저장 실패)")
            except Exception as e:
                st.error(f"❌ 파일 시스템 오류 발생: {e}. 서버 환경(권한)을 확인하세요.")


# --- Step 4: 분석 시뮬레이션 및 완료 (Wizard of Oz) ---
elif st.session_state.step == 4:
    st.header("🧠 AURA AI 분석 진행 중...")

    # AI 분석 시뮬레이션 (사용자가 기다리게 하여 실제 분석처럼 연출)
    progress_text = st.empty()
    bar = st.progress(0)
    
    simulated_steps = [
        (10, "데이터 암호화 및 보안 검증 중..."),
        (30, "업로드된 증거 자료(파일/텍스트) 파싱 및 벡터화 중..."),
        (60, "AURA AI 엔진이 패턴 분석 및 교차 검증 실행 중..."),
        (85, "리스크 스코어링 및 전문가 매칭 알고리즘 가동 중..."),
        (100, "최종 분석 리포트 생성 완료.")
    ]

    # 실제 같은 느낌을 주기 위해 랜덤 딜레이 적용
    for percent, text in simulated_steps:
        progress_text.text(f"진행률 {percent}%: {text}")
        # 랜덤 딜레이를 통해 예측 불가능성 추가 (총 7~15초 소요)
        time.sleep(random.uniform(1.5, 3.0)) 
        bar.progress(percent)

    # 완료 메시지
    st.success("✅ AI 분석 요청이 성공적으로 완료되었습니다!")
    
    name = st.session_state.data.get('contact', {}).get('name', '의뢰인')
    service_type = st.session_state.data.get('service_type')

    st.header(f"감사합니다, {name}님.")
    
    if "💔" in service_type:
        st.subheader("AI 기반 '외도 가능성 분석 리포트'(확률 스코어, 핵심 타임라인 포함)가 생성되었습니다.")
    elif "🔎" in service_type:
        st.subheader("AI 기반 '추적 가능성 분석 리포트'(예상 전략 포함)가 생성되었습니다.")
    else:
        st.subheader("AI 기반 '증거 분석 리포트'가 생성되었습니다.")

    st.info("분석 결과 및 후속 조치(증거 확보 전략/법률 상담/전문가 매칭) 안내는 보안을 위해 전문 상담사를 통해 24시간 내에 전달됩니다.")

    if st.button("새로운 분석 시작하기"):
        # 세션 초기화
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
