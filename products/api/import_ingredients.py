import requests
from django.conf import settings
from products.models import Ingredient
from products.api.ingredients_parser import clean_name, clean_amount, clean_text

API_KEY = settings.FOOD_API_KEY
SERVICE_ID = "I-0050"

def fetch_page(start_idx, end_idx):
    url = f"http://openapi.foodsafetykorea.go.kr/api/{API_KEY}/{SERVICE_ID}/json/{start_idx}/{end_idx}"
    response = requests.get(url)

    if response.status_code != 200:
        print("⚠️ API 오류 상태코드:", response.status_code)
        return []

    data = response.json()
    body = data.get(SERVICE_ID)
    if not body:
        return []

    return body.get("row", [])

def update_ingredients_from_openapi():
    batch = 500
    start = 1
    total_imported = 0
    created_count = 0

    print("➡ 기능성 원료 동기화 시작...")

    while True:
        end = start + batch - 1
        print(f"→ Fetching {start} ~ {end}")

        items = fetch_page(start, end)

        if not items:
            print("✓ 더 이상 데이터가 없어 종료합니다.")
            break

        for item in items:
            raw_name = item.get("RAWMTRL_NM", "").strip()
            if not raw_name:
                continue

            # 이름에서 괄호 안 제거
            name = clean_name(raw_name.split("(")[0].strip())

            # 권장량
            min_rec = clean_amount(item.get("DAY_INTK_LOWLIMIT"))
            max_rec = clean_amount(item.get("DAY_INTK_HIGHLIMIT"))

            effect = clean_text(item.get("PRIMARY_FNCLTY") or "")
            side = clean_text(item.get("IFTKN_ATNT_MATR_CN") or "")

            ingredient, created = Ingredient.objects.update_or_create(
                name=name,
                defaults={
                    "minRecommended": min_rec,
                    "maxRecommended": max_rec,
                    "effect": effect or None,
                    "sideEffect": side or None,
                }
            )

            total_imported += 1

            if created:
                created_count += 1

        start += batch

    print(f"✓ 총 {total_imported}개의 성분이 처리됨.")
    print(f"✓ 총 {created_count}개의 기존 성분이 업데이트됨.")