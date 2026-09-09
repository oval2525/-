import calendar
import datetime
import re
import requests
import streamlit as st

st.set_page_config(
    page_title="월간 학교 급식 달력", page_icon="📅", layout="wide"
)
st.title("📅 우리 학교 월간 급식 달력")
st.caption(
    "선택한 월의 급식 메뉴와 성분별 주의 질환 및 부작용을 한눈에 확인합니다."
)

# 나이스 알레르기 정보 매핑
ALLERGY_MAP = {
    1: "난류",
    2: "우유",
    3: "메밀",
    4: "땅콩",
    5: "대두",
    6: "밀",
    7: "고등어",
    8: "게",
    9: "새우",
    10: "돼지고기",
    11: "복숭아",
    12: "토마토",
    13: "아황산류",
    14: "호두",
    15: "닭고기",
    16: "쇠고기",
    17: "오징어",
    18: "조개류(굴/전복/홍합 포함)",
    19: "잣",
}

# 알레르기 성분별 유발 가능 질환 및 부정적 효과 매핑
ALLERGY_EFFECTS = {
    1: "아토피 피부염, 두드러기, 아나필락시스 쇼크",
    2: "유당불내증(복통·설사), 유아 아토피, 호흡곤란",
    3: "기도 부종, 급성 아나필락시스 쇼크, 구토",
    4: "중증 아나필락시스, 호흡곤란, 기도 막힘",
    5: "소화불량, 피부 발진, 아토피 악화",
    6: "글루텐 유발 장질환(셀리악병), 천식, 팽진",
    7: "히스타민 식중독 유사 증상, 두드러기, 기도 수축",
    8: "급성 알레르기성 비염, 피부 부종, 쇼크",
    9: "구강 알레르기 증후군, 두드러기, 아나필락시스",
    10: "소화기 장애, 피부 가려움증, 蕁麻疹(두드러기)",
    11: "구강 가려움증(구강알레르기증후군), 후두 부종",
    12: "접촉성 피부염, 구강 자극, 두드러기",
    13: "천식 발작, 천명음(숨소리 거칠어짐), 호흡곤란",
    14: "중증 아나필락시스 쇼크, 기도 부종",
    15: "알레르기성 비염, 피부 가려움증, 소화 장애",
    16: "지연성 알레르기 반응(Alpha-gal 반응), 두드러기",
    17: "소화기 반응(구토·설사), 급성 피부 발진",
    18: "패류 독소 위험, 급성 알레르기 쇼크, 기도 부종",
    19: "아나필락시스 쇼크, 구강 부종",
}

# 고위험 알레르기 번호 (해골 아이콘 적용)
HIGH_RISK_ALLERGENS = {1, 3, 4, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19}

# 음식 메뉴 키워드별 이모지 매핑
FOOD_EMOJI_MAP = {
    # 밥류
    "밥": "🍚",
    "볶음밥": "🍳",
    "덮밥": "🍲",
    "비빔밥": "🥗",
    "죽": "🥣",
    "리조또": "🍲",
    "카레": "🍛",
    "하이라이스": "🍛",
    # 국 / 찌개 / 탕 / 수프
    "국": "🍲",
    "찌개": "🥘",
    "탕": "🍲",
    "스프": "🥣",
    "수프": "🥣",
    "수제비": "🥣",
    # 육류 / 고기 요리
    "불고기": "🥩",
    "갈비": "🍖",
    "스테이크": "🥩",
    "삼겹": "🥓",
    "보쌈": "🥩",
    "족발": "🍖",
    "제육": "🥩",
    "닭": "🍗",
    "치킨": "🍗",
    "오리": "🦆",
    "너겟": "🍗",
    "장조림": "🥩",
    # 튀김 / 가스 / 전
    "돈가스": "🥩",
    "돈까스": "🥩",
    "까스": "🍤",
    "가스": "🍤",
    "튀김": "🍤",
    "탕수육": "🥢",
    "전": "🥞",
    "부침": "🥞",
    "크로켓": "🧆",
    "고로케": "🧆",
    # 면류 / 이탈리안
    "국수": "🍜",
    "우동": "🍜",
    "라면": "🍜",
    "짬뽕": "🍜",
    "짜장": "🍜",
    "파스타": "🍝",
    "스파게티": "🍝",
    "잡채": "🥢",
    # 해산물
    "생선": "🐟",
    "구이": "🐟",
    "조림": "🐟",
    "새우": "🦐",
    "오징어": "🦑",
    "낙지": "🐙",
    "문어": "🐙",
    "게": "🦀",
    "조개": "🦪",
    # 분식 / 서양식 / 기타
    "떡볶이": "🍢",
    "순대": "🍢",
    "만두": "🥟",
    "피자": "🍕",
    "버거": "🍔",
    "샌드위치": "🥪",
    "토스트": "🍞",
    # 반찬 / 샐러드 / 김치
    "샐러드": "🥗",
    "무침": "🥗",
    "나물": "🌿",
    "김치": "🥬",
    "깍두기": "🥬",
    "겉절이": "🥬",
    "단무지": "🟡",
    "피클": "🥒",
    "장아찌": "🧄",
    # 디저트 / 음료 / 과일
    "우유": "🥛",
    "요거트": "🍦",
    "요구르트": "🧃",
    "주스": "🧃",
    "즙": "🧃",
    "에이드": "🍹",
    "차": "🍵",
    "빵": "🍞",
    "케이크": "🍰",
    "파이": "🥧",
    "쿠키": "🍪",
    "떡": "🍡",
    "푸딩": "🍮",
    "아이스크림": "🍨",
    "사과": "🍎",
    "바나나": "🍌",
    "포도": "🍇",
    "귤": "🍊",
    "오렌지": "🍊",
    "수박": "🍉",
    "딸기": "🍓",
    "파인애플": "🍍",
    "토마토": "🍅",
    "멜론": "🍈",
}


def get_food_emoji(dish_text):
    """메뉴명을 분석하여 적절한 음식 이모지를 반환합니다."""
    clean_text = re.sub(r"\(?(\d+\.)+\)?", "", dish_text).strip()
    for keyword, emoji in FOOD_EMOJI_MAP.items():
        if keyword in clean_text:
            return emoji
    return "🍱"


def parse_and_format_dish(dish_text, convert_to_text=True):
    """메뉴 텍스트 분석: 알레르기 번호 감지, 위험/경고 아이콘, 번호 변환 및 포함된 알레르기 번호 집합 반환."""
    if not dish_text:
        return "", "", set()

    pattern = r"\(?(\d+\.)+\)?"
    allergy_nums = set()

    for match in re.finditer(pattern, dish_text):
        nums = re.findall(r"\d+", match.group(0))
        for n in nums:
            allergy_nums.add(int(n))

    risk_icon = ""
    if allergy_nums:
        if any(num in HIGH_RISK_ALLERGENS for num in allergy_nums):
            risk_icon = "☠️ "
        else:
            risk_icon = "⚠️ "

    def convert_match(match):
        raw = match.group(0)
        nums = re.findall(r"\d+", raw)
        allergens = [
            ALLERGY_MAP[int(n)] for n in nums if int(n) in ALLERGY_MAP
        ]
        if allergens and convert_to_text:
            return f" :orange[[{', '.join(allergens)}]]"
        return raw

    formatted_text = re.sub(pattern, convert_match, dish_text)
    return risk_icon, formatted_text, allergy_nums


# 사이드바 설정
st.sidebar.header("⚙️ 학교 정보 설정")
office_code = st.sidebar.text_input(
    "시도교육청코드", value="T10", help="기본값: 제주특별자치도교육청(T10)"
)
school_code = st.sidebar.text_input(
    "표준학교코드", value="9290088", help="기본값: 제주중앙고등학교(9290088)"
)

st.sidebar.markdown("---")
st.sidebar.subheader("🍽️ 알레르기 및 부정적 효과 표시 설정")
show_allergen_names = st.sidebar.toggle(
    "알레르기 식품명으로 변환",
    value=True,
    help="체크 시 숫자 대신 [난류, 대두] 형태로 변환합니다.",
)
show_effects_details = st.sidebar.toggle(
    "유발 가능 질환/부작용 표시",
    value=True,
    help="체크 시 해당 식단에 포함된 알레르기 유발 물질의 주의 질환 정보를 아래에 표시합니다.",
)

with st.sidebar.expander("📖 알레르기 성분별 주요 유발 질환 안내표"):
    st.markdown("- **☠️ 표시**: 아나필락시스, 중증 호흡곤란 위험 성분")
    st.markdown("- **⚠️ 표시**: 유당불내증, 두드러기 등 일반 주의 성분\n")
    for k, v in ALLERGY_MAP.items():
        effect = ALLERGY_EFFECTS.get(k, "알레르기 반응")
        st.markdown(f"- **{k}. {v}**: {effect}")

# 메인 날짜/옵션 필터
today = datetime.date.today()
col_y, col_m, col_filter = st.columns([1, 1, 2])
with col_y:
    year = st.selectbox(
        "연도 선택",
        options=list(range(today.year - 1, today.year + 2)),
        index=1,
    )
with col_m:
    month = st.selectbox(
        "월 선택", options=list(range(1, 13)), index=today.month - 1
    )
with col_filter:
    meal_filter = st.radio(
        "급식 종류 선택",
        options=["전체 보기", "중식만 보기", "석식만 보기"],
        index=0,
        horizontal=True,
    )


def fetch_monthly_meals(key, ofcdc_code, schul_code, yr, mo):
    """선택한 월의 급식 정보 가져오기"""
    _, last_day = calendar.monthrange(yr, mo)
    from_ymd = f"{yr}{mo:02d}01"
    to_ymd = f"{yr}{mo:02d}{last_day:02d}"

    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ofcdc_code,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
    }
    response = requests.get(url, params=params, timeout=7)
    return response.json()


if "NEIS_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `NEIS_KEY`가 설정되어 있지 않습니다.")
    st.stop()

neis_key = st.secrets["NEIS_KEY"]

try:
    with st.spinner(f"{year}년 {month}월 급식 정보를 불러오는 중..."):
        res_data = fetch_monthly_meals(
            neis_key, office_code, school_code, year, month
        )

    meal_dict = {}
    if "mealServiceDietInfo" in res_data:
        rows = res_data["mealServiceDietInfo"][1]["row"]
        for row in rows:
            ymd = row.get("MLSV_YMD")
            meal_type = row.get("MMEAL_SC_NM", "급식")
            dish = row.get("DDISH_NM", "")

            raw_lines = [
                d.strip()
                for d in dish.replace("<br/>", "\n").split("\n")
                if d.strip()
            ]
            processed_dishes = []
            for raw_dish in raw_lines:
                emoji = get_food_emoji(raw_dish)
                risk_icon, formatted_dish, allergy_nums = parse_and_format_dish(
                    raw_dish, convert_to_text=show_allergen_names
                )
                processed_dishes.append(
                    (emoji, risk_icon, formatted_dish, allergy_nums)
                )

            meal_dict.setdefault(ymd, {})[meal_type] = processed_dishes

    month_cal = calendar.monthcalendar(year, month)
    weekdays_kr = ["월", "화", "수", "목", "금"]

    st.markdown("---")

    # 달력 렌더링 (월~금)
    for week in month_cal:
        cols = st.columns(5)
        has_school_day = False

        for i in range(5):
            day = week[i]
            with cols[i]:
                if day == 0:
                    st.empty()
                else:
                    has_school_day = True
                    ymd_str = f"{year}{month:02d}{day:02d}"
                    day_meals = meal_dict.get(ymd_str, {})
                    is_today = (
                        year == today.year
                        and month == today.month
                        and day == today.day
                    )

                    with st.container(border=True):
                        if is_today:
                            st.markdown(
                                f"**{month}월 {day}일 ({weekdays_kr[i]})**"
                                " :orange-background[**TODAY**]"
                            )
                        else:
                            st.markdown(
                                f"**{month}월 {day}일 ({weekdays_kr[i]})**"
                            )

                        st.divider()

                        if not day_meals:
                            st.caption("급식 없음 (휴업/방학)")
                        else:
                            displayed_count = 0

                            # 급식 종류별 출력 함수
                            def render_meal_section(m_type, title_color):
                                nonlocal displayed_count
                                displayed_count += 1
                                st.markdown(f"{title_color}[**{m_type}**]")

                                meal_allergy_set = set()
                                for (
                                    emoji,
                                    risk_icon,
                                    dish,
                                    a_nums,
                                ) in day_meals[m_type]:
                                    st.markdown(
                                        f"<span style='font-size:0.85rem;'>• {emoji} {risk_icon}{dish}</span>",
                                        unsafe_allow_html=True,
                                    )
                                    meal_allergy_set.update(a_nums)

                                # 식단별 주의 질환 요약 출력
                                if show_effects_details and meal_allergy_set:
                                    effects_list = [
                                        ALLERGY_EFFECTS[num]
                                        for num in meal_allergy_set
                                        if num in ALLERGY_EFFECTS
                                    ]
                                    if effects_list:
                                        # 유발 가능 질환 중 주요 항목 요약
                                        summary_effects = ", ".join(
                                            list(
                                                dict.fromkeys(
                                                    [
                                                        eff.split(", ")[0]
                                                        for eff in effects_list
                                                    ]
                                                )
                                            )[:3]
                                        )
                                        st.caption(
                                            f"🚨 **주의 질환/부작용**: {summary_effects} 등"
                                        )

                            # 중식
                            if (
                                meal_filter in ["전체 보기", "중식만 보기"]
                                and "중식" in day_meals
                            ):
                                render_meal_section("중식", ":blue[🥣 ]")

                            # 석식
                            if (
                                meal_filter in ["전체 보기", "석식만 보기"]
                                and "석식" in day_meals
                            ):
                                if (
                                    meal_filter == "전체 보기"
                                    and "중식" in day_meals
                                ):
                                    st.write("")
                                render_meal_section("석식", ":red[🌙 ]")

                            # 기타 식단
                            if meal_filter == "전체 보기":
                                for m_type in day_meals:
                                    if m_type not in ["중식", "석식"]:
                                        render_meal_section(
                                            m_type, ":green[🍴 ]"
                                        )

                            if displayed_count == 0:
                                st.caption("해당 식단 없음")

        if has_school_day:
            st.write("")

except requests.exceptions.RequestException as e:
    st.error(
        f"⚠️ 나이스 API 통신 오류: 네트워크 상태를 확인해 주세요. ({e})"
    )
except Exception as e:
    st.error(f"⚠️ 화면 구성 중 오류가 발생했습니다: {e}")
