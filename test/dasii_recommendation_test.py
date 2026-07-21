import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── 성분 데이터 로드 (effect 있는 것만) ──────────────────────────────
with open("../ingredients_export.json", encoding="utf-8") as f:
    all_ingredients = json.load(f)

INGREDIENTS = [
    {
        "name": i["name"],
        "effect": i["effect"],
        "sideEffect": i.get("sideEffect") or [],
        "minRecommended": i.get("minRecommended"),
        "maxRecommended": i.get("maxRecommended"),
    }
    for i in all_ingredients
    if i.get("effect") and len(i["effect"]) > 0
]

# ── 페르소나 정의 ──────────────────────────────────────────────────────
PERSONAS = {
    "야근_직장인_30대_여성": {
        "profile": {
            "goals": ["피로 회복", "면역 강화"],
            "age_range": "30대",
            "gender": "여성",
            "exercise_frequency": "거의 안 함",
            "caffeine_sensitivity": "보통",
            "sleep_hours": "1~4시간",
            "meal_regularity": "불규칙한 편",
            "alcohol_frequency": "거의 안 함",
            "smoking_status": "비흡연",
        },
        # 추천 이유(reason) 또는 성분명에 포함되어야 할 키워드
        "include_keywords": ["피로", "면역", "수면"],
        # 추천 이유(reason) 또는 성분명에 절대 포함되면 안 되는 키워드
        "exclude_keywords": ["카페인"],
    },
    "다이어트_카페인민감_20대_여성": {
        "profile": {
            "goals": ["체지방 감소"],
            "age_range": "20대",
            "gender": "여성",
            "exercise_frequency": "주 1~2회",
            "caffeine_sensitivity": "예민한 편",
            "sleep_hours": "5~7시간",
            "meal_regularity": "다이어트 중",
            "alcohol_frequency": "거의 안 함",
            "smoking_status": "비흡연",
        },
        "include_keywords": ["체지방"],
        "exclude_keywords": ["카페인"],
    },
    "음주흡연_40대_남성": {
        "profile": {
            "goals": ["피로 회복", "면역 강화"],
            "age_range": "40대",
            "gender": "남성",
            "exercise_frequency": "거의 안 함",
            "caffeine_sensitivity": "상관없음",
            "sleep_hours": "5~7시간",
            "meal_regularity": "불규칙한 편",
            "alcohol_frequency": "주 3회 이상",
            "smoking_status": "흡연",
        },
        "include_keywords": ["간", "항산화", "피로"],
        "exclude_keywords": [],
    },
    "갱년기_50대_여성": {
        "profile": {
            "goals": ["면역 강화", "피로 회복"],
            "age_range": "50대",
            "gender": "여성",
            "exercise_frequency": "주 1~2회",
            "caffeine_sensitivity": "보통",
            "sleep_hours": "5~7시간",
            "meal_regularity": "규칙적",
            "alcohol_frequency": "거의 안 함",
            "smoking_status": "비흡연",
        },
        "include_keywords": ["면역", "피로"],
        "exclude_keywords": ["남성만"],
    },
    "다이어트_사무직_30대_여성": {
        "profile": {
            "goals": ["체지방 감소"],
            "age_range": "30대",
            "gender": "여성",
            "exercise_frequency": "거의 안 함",
            "caffeine_sensitivity": "상관없음",
            "sleep_hours": "5~7시간",
            "meal_regularity": "불규칙한 편",
            "alcohol_frequency": "주 1~2회",
            "smoking_status": "비흡연",
        },
        "include_keywords": ["체지방"],
        "exclude_keywords": ["남성만"],
    },
}

# ── 추천 함수 ──────────────────────────────────────────────────────────
def recommend(user_profile: dict, max_retries: int = 3) -> list:
    for attempt in range(max_retries):
        try:
            return _recommend(user_profile)
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  ⏳ 503 에러, {wait}초 후 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise

def _recommend(user_profile: dict) -> list:
    prompt = f"""당신은 건강기능식품 성분 추천 전문가입니다.

아래는 실제 보유 중인 성분 데이터입니다:
{json.dumps(INGREDIENTS, ensure_ascii=False)}

아래는 사용자의 라이프스타일 프로필입니다:
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

규칙:
1. 반드시 위 성분 데이터 목록 안에서만 추천하세요. 목록에 없는 성분을 만들어내지 마세요.
2. 사용자의 목표(goals)와 가장 관련 있는 성분을 우선하세요.
3. sideEffect 항목이 사용자 상태와 충돌하면 반드시 제외하세요.
   - 카페인 민감(caffeine_sensitivity: 예민한 편): 카페인 함유 성분 제외
   - 수면 부족(sleep_hours: 1~4시간): 카페인 함유 성분 제외
   - 성별이 여성: "성인 남성만 섭취" 명시 성분 제외
   - 임산부/수유부인 경우: 관련 주의 성분 제외
4. 생활습관(운동, 음주, 흡연 등)을 추천 우선순위에 반영하세요.
   - 음주 잦음: 간 건강 성분 가중치 상향
   - 흡연: 항산화 성분 가중치 상향
   - 수면 부족: 수면 관련 성분 가중치 상향
5. 정확히 3개를 추천하세요.

아래 JSON 형식으로만 응답하세요:
{{
  "recommendations": [
    {{
      "ingredient_name": "성분명",
      "reason": "추천 이유 (effect 필드 기반, 한 문장)"
    }}
  ]
}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    result = json.loads(response.text)
    return result["recommendations"]


# ── 검증 함수 ──────────────────────────────────────────────────────────
def has_keyword(recommendations: list, keyword: str) -> bool:
    """추천 결과(성분명 + 이유)에 키워드가 하나라도 포함됐는지 확인"""
    return any(
        keyword in r["ingredient_name"] or keyword in r["reason"]
        for r in recommendations
    )

def validate(recommendations: list, include_keywords: list, exclude_keywords: list):
    include_pass = [k for k in include_keywords if has_keyword(recommendations, k)]
    include_fail = [k for k in include_keywords if not has_keyword(recommendations, k)]
    exclude_fail = [k for k in exclude_keywords if has_keyword(recommendations, k)]

    return {
        "include_pass": include_pass,
        "include_fail": include_fail,   # 나왔어야 하는 카테고리인데 없음
        "exclude_fail": exclude_fail,   # 나오면 안 되는 카테고리인데 있음
    }


# ── 실행 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ingredient_names = {i["name"] for i in INGREDIENTS}
    total_pass = 0
    total_fail = 0

    for persona_name, persona_data in PERSONAS.items():
        print(f"\n{'='*60}")
        print(f"페르소나: {persona_name}")
        print(f"{'='*60}")

        recs = recommend(persona_data["profile"])

        print("\n[추천 결과]")
        for r in recs:
            in_db = "✅" if r["ingredient_name"] in ingredient_names else "⚠️ DB에 없음"
            print(f"  {in_db} {r['ingredient_name']}: {r['reason']}")

        result = validate(recs, persona_data["include_keywords"], persona_data["exclude_keywords"])

        print("\n[카테고리 검증]")
        if result["include_pass"]:
            print(f"  ✅ 포함 성공: {result['include_pass']}")
        if result["include_fail"]:
            print(f"  ❌ 포함 실패 (이 카테고리 성분이 없음): {result['include_fail']}")
        if result["exclude_fail"]:
            print(f"  🚨 제외 실패 (나오면 안 되는 키워드 포함): {result['exclude_fail']}")
        if not result["include_fail"] and not result["exclude_fail"]:
            print(f"  🎉 모든 카테고리 검증 통과!")
            total_pass += 1
        else:
            total_fail += 1

        time.sleep(3)  # 페르소나 간 API 호출 간격

    print(f"\n{'='*60}")
    print(f"최종 결과: {total_pass}개 통과 / {total_fail}개 실패 (총 {len(PERSONAS)}개 페르소나)")
    print(f"{'='*60}")