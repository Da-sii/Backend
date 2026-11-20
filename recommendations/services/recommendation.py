import json
import logging
import re

from products.models import Ingredient, ProductIngredient, Product

from django.conf import settings
from google import genai
from google.genai import errors, types

from recommendations.constants import SURVEY_LABEL_MAPS

logger = logging.getLogger(__name__)


client = genai.Client(api_key=settings.GEMINI_API_KEY)

PRIMARY_MODEL = "gemini-3.5-flash-lite"
# 기본 모델이 503(서버 혼잡)일 때 1회 대체 호출 (임시 조치, 사용 빈도 관찰 후 정책 확정)
# 3.1 flash lite: thinking_level="minimal" 호환, 지원 종료 예정(2027-05-07) -> 그 전에 교체 필요
FALLBACK_MODEL = "gemini-3.1-flash-lite"

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
# Gemini 3 계열은 thinking_budget 미지원(400 INVALID_ARGUMENT) -> thinking_level 사용.
# thinking을 완전히 끌 수 없어 가장 낮은 "minimal"을 기본값으로 사용.
def _call_gemini(user_context: dict, ingredient_context: list, thinking_level: str = "minimal") -> list:
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

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
    )

    try:
        response = client.models.generate_content(
            model=PRIMARY_MODEL, contents=prompt, config=config
        )
    except errors.ServerError as e:
        if e.code != 503:
            raise
        logger.warning(f"{PRIMARY_MODEL} 503 -> 대체 모델 {FALLBACK_MODEL} 호출")
        response = client.models.generate_content(
            model=FALLBACK_MODEL, contents=prompt, config=config
        )

    result = json.loads(response.text)

    return result["recommendations"]

PRODUCT_LIMIT = 3

# 함량 단위 -> mg 환산 배수 (CFU 등 개수 단위는 1로 두고 같은 성분 안에서만 비교)
_UNIT_TO_MG = {"g": 1000, "mg": 1, "μg": 0.001, "µg": 0.001, "ug": 0.001, "mcg": 0.001}
_KOREAN_MULTIPLIER = {"억": 10**8, "만": 10**4}
# 예: "750mg", "1,000 mg", "15mg NE", "800μg DFE", "10억CFU", "5억 CFU"
_AMOUNT_PATTERN = re.compile(r"^\s*([\d.,]+)\s*(억|만)?\s*([a-zA-Zμµ]*)")


# 함량 문자열 -> 비교용 숫자 (파싱 불가 시 None)
def _parse_amount(amount: str) -> float | None:
    match = _AMOUNT_PATTERN.match(amount or "")
    if not match:
        return None

    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None

    value *= _KOREAN_MULTIPLIER.get(match.group(2), 1)
    value *= _UNIT_TO_MG.get(match.group(3).lower(), 1)

    return value


# 성분 ID -> 해당 성분을 포함한 제품 리스트 반환 (이미지 포함)
# 정렬: 함량 높은 순 -> 같으면 누적 조회수 높은 순, 최대 PRODUCT_LIMIT개
# 함량 파싱 불가 제품은 맨 뒤로
def get_products_by_ingredient(ingredient_id: int) -> list:
    rows = (
        ProductIngredient.objects
        .filter(ingredient_id=ingredient_id)
        .values("product_id", "amount", "product__viewCount")
    )

    # 한 제품에 같은 성분이 여러 행이면 가장 큰 함량 사용
    candidates = {}
    for row in rows:
        amount = _parse_amount(row["amount"])
        prev = candidates.get(row["product_id"])
        if prev is None or (amount is not None and (prev[0] is None or amount > prev[0])):
            candidates[row["product_id"]] = (amount, row["product__viewCount"])

    top_ids = sorted(
        candidates,
        key=lambda pid: (
            candidates[pid][0] is None,
            -(candidates[pid][0] or 0),
            -candidates[pid][1],
            pid,  # 동점 시 순서 고정
        ),
    )[:PRODUCT_LIMIT]

    products = Product.objects.filter(id__in=top_ids).prefetch_related("images")
    products_by_id = {p.id: p for p in products}

    result = []
    for pid in top_ids:
        p = products_by_id[pid]
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

        products = get_products_by_ingredient(rec["ingredient_id"])

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