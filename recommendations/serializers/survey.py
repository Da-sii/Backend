from rest_framework import serializers

from recommendations.constants import GOAL_CHOICES, AGE_RANGE_LABELS, GENDER_LABELS, EXERCISE_LABELS, CAFFEINE_LABELS, \
    SLEEP_LABELS, MEAL_LABELS, ALCOHOL_LABELS, SMOKING_LABELS


class SurveySerializer(serializers.Serializer):
    """온보딩 설문 입력 검증 (모델과 무관, 순수 입력 검증용)"""

    goals = serializers.ListField(
        child=serializers.ChoiceField(choices=GOAL_CHOICES),
        allow_empty=False,
    )
    age_range = serializers.ChoiceField(choices=list(AGE_RANGE_LABELS.keys()))
    gender = serializers.ChoiceField(choices=list(GENDER_LABELS.keys()))
    exercise_frequency = serializers.ChoiceField(choices=list(EXERCISE_LABELS.keys()))
    caffeine_sensitivity = serializers.ChoiceField(choices=list(CAFFEINE_LABELS.keys()))
    sleep_hours = serializers.ChoiceField(choices=list(SLEEP_LABELS.keys()))
    meal_regularity = serializers.ChoiceField(choices=list(MEAL_LABELS.keys()))
    alcohol_frequency = serializers.ChoiceField(choices=list(ALCOHOL_LABELS.keys()))
    smoking_status = serializers.ChoiceField(choices=list(SMOKING_LABELS.keys()))