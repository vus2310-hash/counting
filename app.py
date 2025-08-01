import streamlit as st
import pandas as pd
import re
from collections import Counter, OrderedDict

st.title("7월 편현준 데이터 맞춤형 자동 분석기")

# 기본 변환 규칙 (치환 리스트 형태)
default_replacements = {
    "simple": "도수9",
    "도수7": "도수8",
    "16 1/2": "도수8",
    "도수9*": "도수9",
}

# 기본 제외 키워드
default_exclude_keywords = ["FES", "기구", "예약", "예약문자"]

def apply_replacements(text, replacements):
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def clean_treatment_text(text, exclude_keywords):
    # 괄호 내용 제거
    text = re.sub(r'\([^)]*\)', '', text)
    # 제외 키워드 필터링
    for kw in exclude_keywords:
        text = text.replace(kw, "")
    # 안내 멘트 (ex. 9시, 치료먼저 등) 제거
    text = re.sub(r'\d{1,2}시[^\s]*', '', text)
    text = text.replace("치료먼저", "").replace("기구먼저", "")
    # 중복 공백 제거
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_name_and_treatment(val, replacements, exclude_keywords, custom_rules):
    if pd.isnull(val):
        return None, None
    sval = str(val).strip()
    if not sval or "점심" in sval or sval == "ㅡ":
        return None, None

    # 이름 추출 (숫자+이름+치료 패턴)
    m = re.match(r'(?:\d{3,5}\s*)?(\(?[가-힣]{2,4}\)?)\s+(.+)', sval)
    if not m:
        return None, None
    name = m.group(1).replace("(", "").replace(")", "")
    treat = m.group(2).strip()

    # 기본 치환
    treat = apply_replacements(treat, replacements)

    # 사용자 추가 치환 규칙 적용
    for rule in custom_rules:
        parts = rule.split("=>")
        if len(parts) == 2:
            src = parts[0].strip()
            dst = parts[1].strip()
            treat = treat.replace(src, dst)

    # 제외 키워드 및 안내 문구 제거
    treat = clean_treatment_text(treat, exclude_keywords)

    # 특정 이름별 맞춤 변환 예시
    if name == "곽순욱":
        treat = "도수8"
    if name == "박한나" and "도수5" in treat and "평가" in treat:
        treat = "도수8"
    if name == "강대환" and "pain5" in treat and "평가" in treat:
        treat = "pain9"
    if name == "주영민" and "평가" in treat:
        treat = "NDT"
    if name == "문장민" and "도수4" in treat and "평가" in treat:
        treat = "도수9"
    if name == "변인혁" and "도수5" in treat and "평가" in treat:
        treat = "도수8"
    if name == "홍한나":
        treat = "도수9"
    if name == "이성범":
        treat = "도수9"

    # 빈 문자열이나 FES만 남으면 무시
    if treat == "" or treat == "FES":
        return None, None

    return name, treat

# 사용자 입력폼
st.sidebar.header("사용자 맞춤 변환 규칙")
replace_input = st.sidebar.text_area(
    "치환 규칙 (한 줄에 '원본=>대상' 형식)",
    value="도수7 => 도수8\nsimple => 도수9\n16 1/2 => 도수8\n도수9* => 도수9",
    height=120
)
exclude_input = st.sidebar.text_area(
    "제외할 키워드 (쉼표로 구분)",
    value="FES,기구,예약,예약문자",
    height=60
)

custom_rules = [line.strip() for line in replace_input.split("\n") if line.strip()]
exclude_keywords = [kw.strip() for kw in exclude_input.split(",") if kw.strip()]

uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    days = [str(i) for i in range(1, 32)]
    monthly_seen = OrderedDict()

    for day in days:
        target_sheets = [s for s in xls.sheet_names if day in s]
        for sheet in target_sheets:
            df = pd.read_excel(xls, sheet_name=sheet, header=1)
            colname = next((c for c in df.columns if "편현준" in str(c)), None)
            if not colname:
                continue
            idx = list(df.columns).index(colname)
            right_col = df.columns[idx + 1] if idx + 1 < len(df.columns) else None
            if not right_col:
                continue
            col_data = df[right_col].dropna().tolist()
            for val in col_data:
                name, treat = extract_name_and_treatment(val, {}, exclude_keywords, custom_rules)
                if name and name not in monthly_seen:
                    monthly_seen[name] = treat

    counts = Counter(monthly_seen.values())
    st.subheader("이름별 첫 등장 치료명")
    st.table(monthly_seen)
    st.subheader("치료명별 집계")
    st.table(counts)
else:
    st.info("왼쪽 사이드바에서 규칙을 조정하고 엑셀 파일을 업로드 해주세요.")
