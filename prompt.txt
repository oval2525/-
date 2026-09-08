import calendar
from datetime import datetime
import requests
import streamlit as st

# 페이지 설정
st.set_page_config(page_title="우리 학교 한 달 급식 달력", layout="wide")

st.title("🍱 우리 학교 한 달 급식 달력")
st.caption("나이스(NEIS) 교육청 Open API를 활용한 월별 급식 조회 서비스입니다.")

# 1. 학교 검색 및 설정 사이드바
st.sidebar.header("🔍 학교 검색")
school_name = st.sidebar.text_input("학교 이름을 입력하세요", value="서울고등학교")

# 연도 및 월 선택
today = datetime.now()
selected_year = st.sidebar.number_input(
    "연도", min_value=2020, max_value=2030, value=today.year
)
selected_month = st.sidebar.selectbox(
    "월", list(range(1, 13)), index=today.month - 1
)


# 나이스 API: 학교 코드 검색 함수
@st.cache_data(ttl=3600)
def search_school(name):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "pIndex": 1, "pSize": 10, "SCHUL_NM": name}
    try:
        res = requests.get(url, params=params).json()
        if "schoolInfo" in res:
            return res["schoolInfo"][1]["row"]
        return []
    except Exception:
        return []


# 나이스 API: 월별 급식 정보 조회 함수
@st.cache_data(ttl=3600)
def get_monthly_diet(atpt_code, sd_code, year, month):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    # YYYYMM 형식
    ym = f"{year}{month:02d}"
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": sd_code,
        "MLSV_YMD": ym,
    }
    try:
        res = requests.get(url, params=params).json()
        diet_data = {}
        if "mealServiceDietInfo" in res:
            rows = res["mealServiceDietInfo"][1]["row"]
            for row in rows:
                day = int(row["MLSV_YMD"][-2:])
                # 알레르기 정보 숫자 및 원산지 등 정리, HTML 태그(<br/>) 변환
                dish_text = row["DDISH_NM"].replace("<br/>", "\n")
                # 숫자(알레르기 요인) 제거 원할 경우 정규식 추가 가능
                diet_data[day] = dish_text
        return diet_data
    except Exception:
        return {}


# 학교 검색 수행
schools = search_school(school_name)

if not schools:
    st.warning("학교를 찾을 수 없습니다. 정확한 학교명을 입력해 주세요.")
else:
    # 검색된 학교가 여러 개일 경우 선택
    school_options = {
        f"{s['SCHUL_NM']} ({s['LCTN_SC_NM']})": s for s in schools
    }
    selected_school_label = st.sidebar.selectbox(
        "학교 선택", list(school_options.keys())
    )
    selected_school = school_options[selected_school_label]

    atpt_code = selected_school["ATPT_OFCDC_SC_CODE"]
    sd_code = selected_school["SD_SCHUL_CODE"]

    st.subheader(
        f"📅 {selected_school['SCHUL_NM']} - {selected_year}년 {selected_month}월 급식표"
    )

    # 급식 데이터 가져오기
    diet_dict = get_monthly_diet(
        atpt_code, sd_code, selected_year, selected_month
    )

    # 달력 데이터 생성 (calendar 모듈 활용)
    cal = calendar.Calendar(firstweekday=6)  # 일요일부터 시작
    month_days = cal.monthdayscalendar(selected_year, selected_month)

    # 요일 헤더
    days_of_week = ["일", "월", "화", "수", "목", "금", "토"]
    cols = st.columns(7)
    for idx, day_name in enumerate(days_of_week):
        cols[idx].markdown(f"**{day_name}**", help=None)

    st.markdown("---")

    # 달력 출력
    for week in month_days:
        week_cols = st.columns(7)
        for idx, day in enumerate(week):
            with week_cols[idx]:
                if day != 0:
                    # 날짜 표시
                    st.markdown(f"### {day}")

                    # 해당 날짜에 급식이 있는 경우 출력
                    if day in diet_dict:
                        st.info(diet_dict[day])
                    else:
                        # 주말이거나 급식이 없는 날
                        if idx in [0, 6]:  # 토요일, 일요일
                            st.caption("주말")
                        else:
                            st.caption("급식 없음")
                else:
                    # 이번 달에 해당하지 않는 칸
                    st.write("")
