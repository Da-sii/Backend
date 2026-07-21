"""설문 선택지 정의"""

# Q1 목표 (다중 선택)
GOAL_CHOICES = [
    "체지방 감소",
    "근육 증가",
    "피로 회복",
    "면역 강화",
    "소화 개선",
    "혈당 관리",
    "기타",
]

# Q2 나이대
AGE_RANGE_LABELS = {
    "10s": "10대",
    "20s": "20대",
    "30s": "30대",
    "40s": "40대",
    "50s": "50대",
    "60s+": "60대 이상",
}

# Q3 성별
GENDER_LABELS = {
    "M": "남성",
    "F": "여성",
    "N": "선택 안 함",
}

# Q4 운동 빈도
EXERCISE_LABELS = {
    "none": "거의 안 함",
    "1_2": "주 1~2회",
    "3_plus": "주 3회 이상",
}

# Q5 카페인 민감도
CAFFEINE_LABELS = {
    "sensitive": "예민한 편",
    "normal": "보통",
    "none": "상관없음",
}

# Q6 수면 시간
SLEEP_LABELS = {
    "8_plus": "8시간 이상",
    "5_7": "5~7시간",
    "1_4": "1~4시간",
}

# Q7 식사 규칙성
MEAL_LABELS = {
    "regular": "규칙적",
    "irregular": "불규칙한 편",
    "diet": "다이어트 중",
}

# Q8 음주 빈도
ALCOHOL_LABELS = {
    "none": "거의 안 함",
    "1_2": "주 1~2회",
    "3_plus": "주 3회 이상",
}

# Q9 흡연 여부
SMOKING_LABELS = {
    "none": "비흡연",
    "smoking": "흡연",
    "quitting": "금연 중",
}

# 설문 필드명 -> 라벨 매핑 (변환 시 순회용)
SURVEY_LABEL_MAPS = {
    "age_range": AGE_RANGE_LABELS,
    "gender": GENDER_LABELS,
    "exercise_frequency": EXERCISE_LABELS,
    "caffeine_sensitivity": CAFFEINE_LABELS,
    "sleep_hours": SLEEP_LABELS,
    "meal_regularity": MEAL_LABELS,
    "alcohol_frequency": ALCOHOL_LABELS,
    "smoking_status": SMOKING_LABELS,
}