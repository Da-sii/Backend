
# UserProfile 모델 -> Gemini 프롬프트용 딕셔너리 변환
def _build_user_context(profile) -> dict:
    return {
        "goals" : profile.goals,
        "age_range": profile.get_age_range_display(),
        "gender": profile.get_gender_display(),
        "exercise_frequency": profile.get_exercise_frequency_display(),
        "caffeine_sensitivity": profile.get_caffeine_sensitivity_display(),
        "sleep_hours": profile.get_sleep_hours_display(),
        "meal_regularity": profile.get_meal_regularity_display(),
        "alcohol_frequency": profile.get_alcohol_frequency_display(),
        "smoking_status": profile.get_smoking_status_display(),
    }

# DB 성분 전체 -> Gemini 프롬프트형 리스트 변환
# def _build_ingredient_context() :
#
#
# def get_recommendations(user_profile) -> list:
#     # 사용자 컨텍스트 구성
#     user_context = _build_user_context(user_profile)
#
#     # 성분 DB 전체 조회
#     ingredient_context = _build_ingredient_context()