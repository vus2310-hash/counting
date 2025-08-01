import streamlit as st
import pandas as pd
import re
from collections import Counter, OrderedDict

st.title("7월 편현준 데이터 분석 (고정규칙 포함 변환 가능)")

# 기본 변환 규칙
default_replacements = {
    "simple": "도수9",
    "도수7": "도수8",
    "16 1/2": "도수8",
    "도수9*": "도수9",
}

# 기본 제외 키워드
default_exclude_keywords = ["FES", "기구", "예약", "예약문자"]

# 환자별 고정 규칙 (입력 폼에서 직접 작성)
# 예시 형식: 곽순욱=>도수8
patient_rule_input = st.sidebar.text_area(
    "환자별 고정 변환 규칙 (한 줄에 '이름=>치료명' 형식)", 
    value="곽순욱=>도수8\n박한나=>도수8\n강대환=>pain9\n주영민=>NDT\n문장민=>도수9\n변인혁=>도수8\n홍한나=>도수9\n이성범=>도수9",
    height=180
)

def parse_patient_rules(text):
    rules = {}
    for line in text.split("\n"):
        if "=>" in line:
            name, treat = line.split("=>", 1)
            rules[name.strip()] = treat.strip()
    return rules

patient_rule_map = parse_patient_rules(patient_rule_input)

def apply_replacements(text, replacements):
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def clean_treatment_text(text, exclude_keywords):
    text = re.sub(r'\([^)]*\)', '', text)
    for kw in exclude_keywords:
        text = text.replace(kw, "")
    text = re.sub(r'\d{1,2}시[^\s]*', '', text)
    text = text.replace("치료먼저", "").replace("기구먼저", "")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_name_and_treatment(val, replacements, exclude_keywords, custom_rules, patient_rules):
    if pd.isnull(val):
        return None, None
    sval = str(val).strip()
    if not sval or "점심" in sval or sval == "ㅡ":
        return None, None

    m = re.match(r'(?:\d{3,5}\s*)?(\(?[가-힣]{2,4}\)?)\s+(.+)', sval)
    if not m:
        return None, None
    name = m.group(1).replace("(", "").replace(")", "")
    treat = m.group(2).strip()

    # 환자별 고정 규칙 우선 적용
    if name in patient_rules:
        return name, patient_rules[name]

    treat = apply_replacements(treat, replacements)
    for rule in custom_rules:
        parts = rule.split("=>")
        if len(parts) == 2:
            src = parts[0].strip()
            dst = parts[1].strip()
            treat = treat.replace(src, dst)
    treat = clean_treatment_text(treat, exclude_keywords)
    if treat == "" or treat == "FES":
        return None, None

    return name, treat

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
    all_day_results = {}
    monthly_seen = OrderedDict()

    for day in days:
        target_sheets = [s for s in xls.sheet_names if day in s]
        daily_seen = OrderedDict()
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
                name, treat = extract_name_and_treatment(val, {}, exclude_keywords, custom_rules, patient_rule_map)
                if name:
                    if name not in daily_seen:
                        daily_seen[name] = treat
                    if name not in monthly_seen:
                        monthly_seen[name] = treat
        if daily_seen:
            all_day_results[day] = daily_seen

    for day, results in all_day_results.items():
        st.subheader(f"{day}일 분석 결과")
        st.write("이름별 첫 등장 치료명")
        st.table(results)
        st.write("치료명별 집계")
        st.table(Counter(results.values()))

    st.subheader("7월 전체 월 총계")
    st.write("이름별 첫 등장 치료명")
    st.table(monthly_seen)
    st.write("치료명별 집계")
    st.table(Counter(monthly_seen.values()))
else:
    st.info("왼쪽 사이드바에서 규칙을 조정하고 엑셀 파일을 업로드 해주세요.")
