import json
import logging

from products.models import Ingredient, ProductIngredient, Product

from django.conf import settings
from google import genai
from google.genai import types

from recommendations.constants import SURVEY_LABEL_MAPS

logger = logging.getLogger(__name__)


client = genai.Client(api_key=settings.GEMINI_API_KEY)

# UserProfile 모델 -> Gemini 프롬프트용 딕셔너리 변환
def _build_user_context(survey: dict) -> dict:
    context = {"goals": survey["goals"]}  # goals는 이미 한글이라 변환 불필요

    for field, label_map in SURVEY_LABEL_MAPS.items():
        context[field] = label_map[survey[field]]

    return context

# DB 성분 -> Gemini 프롬프트형 리스트 변환 (사용자가 선택한 goals와 하나라도 겹치는 성분만)
def _build_ingredient_context(goals: list) -> list:
    ingredients = Ingredient.objects.values(
        "id", "name", "effect", "sideEffect", "minRecommended", "maxRecommended", "goals"
    )

    selected_goals = set(goals)

    return [
        {
            "id": i["id"],
            "name": i["name"],
            "effect": i["effect"] or [],
            "sideEffect": i["sideEffect"] or [],
            "minRecommended": i["minRecommended"],
            "maxRecommended": i["maxRecommended"],
            "goals": i["goals"] or [],
        }
        for i in ingredients
        if i["effect"] and selected_goals & set(i["goals"] or [])
    ]

# Gemini API 호출 -> 추천 성분 리스트 반환
def _call_gemini(user_context: dict, ingredient_context: list) -> list:
    prompt = f"""당신은 건강기능식품 성분 추천 전문가입니다.

    아래는 실제 보유 중인 성분 데이터입니다:
    {json.dumps(ingredient_context, ensure_ascii=False)}

    아래는 사용자의 라이프스타일 프로필입니다:
    {json.dumps(user_context, ensure_ascii=False, indent=2)}

    규칙:
    1. 반드시 위 성분 데이터 목록 안에서만 추천하세요. 목록에 없는 성분을 만들어내지 마세요.
    2. 각 성분의 goals 필드와 사용자의 목표(goals)가 겹치는 개수가 많을수록 우선하세요.
    3. sideEffect 항목이 사용자 상태와 충돌하면 반드시 제외하세요.
       - caffeine_sensitivity가 "예민한 편": 카페인 함유 성분 제외
       - sleep_hours가 "1~4시간": 카페인 함유 성분 제외
       - gender가 "여성": "성인 남성만 섭취" 명시 성분 제외
    4. 생활습관을 추천 우선순위에 반영하세요.
       - alcohol_frequency가 "주 3회 이상": 간 건강 성분 가중치 상향
       - smoking_status가 "흡연" 또는 "금연 중": 항산화 성분 가중치 상향
       - sleep_hours가 "1~4시간": 수면 관련 성분 가중치 상향
    5. 정확히 3개를 추천하세요. fit_score 높은 순으로 정렬하세요.
    6. fit_score는 0~100 사이 정수로, 사용자 프로필과의 적합도를 나타냅니다.

    아래 JSON 형식으로만 응답하세요:
    {{
      "recommendations": [
        {{
          "ingredient_id": 성분 ID (정수),
          "ingredient_name": "성분명",
          "intro": "이 성분에 대한 한 줄 소개 (effect 필드 기반, 2~3문장)",
          "reason": "이 사용자에게 추천하는 이유 (사용자 프로필 기반, 한 문장)",
          "fit_score": 적합도 점수 (0~100 정수)
        }}
      ]
    }}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )

    result = json.loads(response.text)

    return result["recommendations"]

# 성분 ID -> 해당 성분을 포함한 제품 리스트 반환 (이미지 포함)
def _get_products_by_ingredient(ingredient_id: int) -> list:
    product_ids = (
        ProductIngredient.objects
        .filter(ingredient_id=ingredient_id)
        .values_list("product_id", flat=True)
        .distinct()
    )

    products = Product.objects.filter(id__in=product_ids).prefetch_related("images")

    result = []
    for p in products:
        images = [img.url for img in p.images.all()]
        result.append({
            "id": p.id,
            "name": p.name,
            "company": p.company,
            "thumbnail": images[0] if images else None,
        })

    return result

# 메인 추천 함수
def get_recommendations(survey: dict) -> list:
    # 사용자 컨텍스트 구성
    user_context = _build_user_context(survey)

    # 성분 DB 조회 (선택한 goals와 관련 있는 성분만)
    ingredient_context = _build_ingredient_context(survey["goals"])

    # Gemini 호출
    raw_recommendations = _call_gemini(user_context, ingredient_context)

    # 응답 검증 + 제품 조회 결합
    valid_ingredient_ids = {i["id"] for i in ingredient_context}
    result = []

    for rec in raw_recommendations:
        if rec["ingredient_id"] not in valid_ingredient_ids:
            logger.warning(f"Gemini가 DB에 없는 성분 추천: {rec['ingredient_name']} (id={rec['ingredient_id']})")
            continue

        products = _get_products_by_ingredient(rec["ingredient_id"])

        result.append({
            "ingredient_id": rec["ingredient_id"],
            "ingredient_name": rec["ingredient_name"],
            "intro": rec["intro"],
            "reason": rec["reason"],
            "fit_score": rec["fit_score"],
            "products": products,
        })

    result.sort(key=lambda r: r["fit_score"], reverse=True)

    return result[:3]