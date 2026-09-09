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
    "선택한 월의 급식 메뉴를 주간 달력 형태로 한눈에 확인합니다."
)

# 알레르기 정보 매핑
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
    # 국 / 찌개 / 탕 / 스프
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
    "튀김": "🍤",
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
    # 알레르기 번호 제거 후 pure text에서 키워드 검색
    clean_text = re.sub(r"\(?(\d+\.)+\)?", "", dish_text).strip()
    for keyword, emoji in FOOD_EMOJI_MAP.items():
        if keyword in clean_text:
            return emoji
    return "🍱"  # 매칭되는 키워드가 없을 때 기본 이모지


def replace_allergy_codes(
    dish_text, convert_to_text=True, target_allergens=None
):
    """
    메뉴명 뒤의 알레르기 번호를 감지하여 한글 식재료명으로 치환하고,
    사용자가 주의 선택한 알레르기가 있는 경우 경고 이모지(⚠️)와 위험 여부(is_warning)를 반환합니다.
    """
    if target_allergens is None:
        target_allergens = []

    if not dish_text:
        return dish_text, False

    is_warning = False

    def convert_match(match):
        nonlocal is_warning
        raw = match.group(0)
        nums = [int(n) for n in re.findall(r"\d+", raw)]

        # 선택한 알레르기 번호와 일치하는 항목이 있는지 확인
        if any(n in target_allergens for n in nums):
            is_warning = True

        if convert_to_text:
            allergens = [
                ALLERGY_MAP[n] for n in nums if n in ALLERGY_MAP
            ]
            if allergens:
                # 주의 대상인 경우 빨간색 강조 표시
                if is_warning:
                    return f" :red[[{', '.join(allergens)}]]"
                return f" :orange[[{', '.join(allergens)}]]"
        return raw

    pattern = r"\(?(\d+\.)+\)?"
    converted_text = re.sub(pattern, convert_match, dish_text)

    return converted_text, is_warning


st.sidebar.header("⚙️ 학교 정보 설정")
office_code = st.sidebar.text_input(
    "시도교육청코드", value="T10", help="기본값: 제주특별자치도교육청(T10)"
)
school_code = st.sidebar.text_input(
    "표준학교코드", value="9290088", help="기본값: 제주중앙고등학교(9290088)"
)

st.sidebar.markdown("---")
st.sidebar.subheader("🍽️ 알레르기 설정")
show_allergen_names = st.sidebar.toggle(
    "알레르기 식품명으로 변환",
    value=True,
    help="체크 시 숫자(예: 1. 5.) 대신 [난류, 대두] 형태로 변환하여 표시합니다.",
)

# 🚨 사용자 주의 알레르기 선택 멀티셀렉트 박스
selected_allergens = st.sidebar.multiselect(
    "⚠️ 주의할 알레르기 선택",
    options=list(ALLERGY_MAP.keys()),
    format_func=lambda x: f"{x}. {ALLERGY_MAP[x]}",
    help="선택한 알레르기 성분이 포함된 메뉴는 빨간색 글씨와 ⚠️ 위험 아이콘으로 표시됩니다.",
)

with st.sidebar.expander("📖 나이스 알레르기 번호 안내표"):
    table_md = "\n".join([f"- **{k}번**: {v}" for k, v in ALLERGY_MAP.items()])
    st.markdown(table_md)

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
    """선택한 월의 1일부터 말일까지의 급식을 조회합니다."""
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

            # 원본 메뉴명에서 이모지 추출 후 알레르기 번호 변환 진행
            raw_lines = [
                d.strip()
                for d in dish.replace("<br/>", "\n").split("\n")
                if d.strip()
            ]
            processed_dishes = []
            for raw_dish in raw_lines:
                emoji = get_food_emoji(raw_dish)
                formatted_dish, is_warning = replace_allergy_codes(
                    raw_dish,
                    convert_to_text=show_allergen_names,
                    target_allergens=selected_allergens,
                )
                processed_dishes.append((emoji, formatted_dish, is_warning))

            meal_dict.setdefault(ymd, {})[meal_type] = processed_dishes

    month_cal = calendar.monthcalendar(year, month)
    weekdays_kr = ["월", "화", "수", "목", "금"]

    st.markdown("---")

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

                            # 공통 렌더링 함수
                            def render_dishes(dishes):
                                for emoji, dish, is_warning in dishes:
                                    if is_warning:
                                        # 빨간색 텍스트 + 위험 아이콘 ⚠️ 표시
                                        st.markdown(
                                            f"<span style='font-size:0.85rem; color:#FF4B4B; font-weight:bold;'>"
                                            f"⚠️ {emoji} {dish}</span>",
                                            unsafe_allow_html=True,
                                        )
                                    else:
                                        st.markdown(
                                            f"<span style='font-size:0.85rem;'>"
                                            f"• {emoji} {dish}</span>",
                                            unsafe_allow_html=True,
                                        )

                            if (
                                meal_filter in ["전체 보기", "중식만 보기"]
                                and "중식" in day_meals
                            ):
                                displayed_count += 1
                                st.markdown(":blue[**🥣 중식**]")
                                render_dishes(day_meals["중식"])

                            if (
                                meal_filter in ["전체 보기", "석식만 보기"]
                                and "석식" in day_meals
                            ):
                                displayed_count += 1
                                if (
                                    meal_filter == "전체 보기"
                                    and "중식" in day_meals
                                ):
                                    st.write("")
                                st.markdown(":red[**🌙 석식**]")
                                render_dishes(day_meals["석식"])

                            if meal_filter == "전체 보기":
                                for m_type, dishes in day_meals.items():
                                    if m_type not in ["중식", "석식"]:
                                        displayed_count += 1
                                        st.markdown(
                                            f":green[**🍴 {m_type}**]"
                                        )
                                        render_dishes(dishes)

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
