"""
products/management/commands/crawl_garcinia_to_csv.py

식품안전나라 API에서 가르시니아 제품 데이터를 수집하여 CSV로 저장합니다.
퍼지매칭으로 ingredient 이름을 정제합니다.

사용법:
    python manage.py crawl_garcinia_to_csv

출력 파일:
    data/products.csv
    data/product_ingredients.csv
    data/ingredients.csv
    data/unmatched_ingredients.csv  ← 매칭 실패한 것들 (수동 검토용)

필요한 패키지:
    pip install requests rapidfuzz
"""

import re
import csv
import time
import os
import requests
import xml.etree.ElementTree as ET

from rapidfuzz import process, fuzz
from django.core.management.base import BaseCommand
from products.models import Ingredient


# ------------------------------------------------------------------ #
#  설정값
# ------------------------------------------------------------------ #
API_KEY    = "646f0911e9b341a49cb3"
SERVICE_ID = "I0030"
BASE_URL   = f"https://openapi.foodsafetykorea.go.kr/api/{API_KEY}/{SERVICE_ID}/xml"
BATCH_SIZE = 1000
OUTPUT_DIR = "data"

GARCINIA_KEYWORDS    = ["가르시니아"]
FUZZY_THRESHOLD      = 90   # 90% 이상 유사도면 매칭

# ------------------------------------------------------------------ #
#  고시형 기본 원료 목록 (DB에 없는 것들)
# ------------------------------------------------------------------ #
STANDARD_INGREDIENTS = [
    "가르시니아캄보지아 추출물", "녹차추출물", "공액리놀레산",
    "키토산", "키토올리고당", "바나바잎추출물", "프로바이오틱스",
    "아연", "비타민A", "비타민B1", "비타민B2", "비타민B6", "비타민B12",
    "비타민C", "비타민D", "비타민E", "비타민K", "나이아신", "판토텐산",
    "비오틴", "엽산", "칼슘", "마그네슘", "철", "구리", "망간",
    "셀레늄", "요오드", "크롬", "몰리브덴", "인", "칼륨", "염소",
    "식이섬유", "난소화성말토덱스트린", "알로에겔", "차전자피식이섬유",
    "프락토올리고당", "이눌린", "치커리추출물", "대두이소플라본",
    "코엔자임Q10", "오메가3", "EPA", "DHA", "홍삼", "인삼",
    "밀크시슬추출물", "은행잎추출물", "루테인", "헤마토코쿠스추출물",
    "글루코사민", "N-아세틸글루코사민", "콜라겐", "히알루론산",
    "락토페린", "레시틴", "스쿠알렌", "조단백질", "포스콜린",
    "카테킨", "코로솔산", "자일로올리고당", "자일리톨",
]

# ------------------------------------------------------------------ #
#  원료명 정확 매핑 테이블 (퍼지매칭 전 먼저 체크)
# ------------------------------------------------------------------ #
EXACT_NAME_MAP = {
    # 가르시니아 HCA 관련
    "hydroxycitric acid":               "가르시니아캄보지아 추출물",
    "hydroxycitiric acid":              "가르시니아캄보지아 추출물",
    "hydroxycitiricacid":               "가르시니아캄보지아 추출물",
    "hydroxycitricacid":                "가르시니아캄보지아 추출물",
    "hydroxycitric aicd":               "가르시니아캄보지아 추출물",
    "hca":                              "가르시니아캄보지아 추출물",
    "hca 함량":                         "가르시니아캄보지아 추출물",
    "가르시니아캄보지아추출물":          "가르시니아캄보지아 추출물",
    "가르시니아캄보지아추출물 정":       "가르시니아캄보지아 추출물",
    "-hydroxycitric acid":              "가르시니아캄보지아 추출물",
    "- 총 hydroxycitric acid":          "가르시니아캄보지아 추출물",

    # 프로바이오틱스
    "프로바이오틱스 수":                "프로바이오틱스",
    "프로바이오틱스수":                 "프로바이오틱스",

    # 공백 오류
    "아 연":   "아연",
    "망 간":   "망간",
    "셀 렌":   "셀레늄",
    "셀레 늄": "셀레늄",
    "철 분":   "철",
}

# ------------------------------------------------------------------ #
#  원료명 → 카테고리 id 매핑
# ------------------------------------------------------------------ #
INGREDIENT_CATEGORY_MAP = {
    "가르시니아캄보지아 추출물": [1],
    "녹차추출물":               [1],
    "공액리놀레산":             [1],
    "키토산":                  [1],
    "키토올리고당":             [1],
    "바나바잎추출물":           [2],
    "난소화성말토덱스트린":      [2],
    "프로바이오틱스":           [3],
    "알로에겔":                [3],
    "차전자피식이섬유":          [3],
    "프락토올리고당":           [3],
}


# ------------------------------------------------------------------ #
#  퍼지매칭 클래스
# ------------------------------------------------------------------ #
class IngredientMatcher:
    def __init__(self, stdout):
        self.stdout = stdout

        # DB에서 개별인정형 목록 로드
        db_names = list(Ingredient.objects.values_list("name", flat=True))

        # 고시형 기본 목록 합치기
        self.all_candidates = list(set(db_names + STANDARD_INGREDIENTS))
        self.stdout.write(f"  퍼지매칭 기준 목록: {len(self.all_candidates)}개")

        # 매칭 결과 캐시 (같은 이름 반복 매칭 방지)
        self.cache = {}
        self.unmatched = []   # 매칭 실패 목록

    def match(self, cleaned_name: str, raw_name: str) -> tuple[str, str]:
        """
        ingredient 이름 매칭
        반환: (최종 이름, 매칭 방법)
        """
        if cleaned_name in self.cache:
            return self.cache[cleaned_name]

        # 1. 정확 매핑 테이블
        exact = EXACT_NAME_MAP.get(cleaned_name.lower().strip())
        if exact:
            self.cache[cleaned_name] = (exact, "exact_map")
            return exact, "exact_map"

        # 2. 퍼지매칭
        result = process.extractOne(
            cleaned_name,
            self.all_candidates,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=FUZZY_THRESHOLD
        )

        if result:
            matched_name, score, _ = result
            self.cache[cleaned_name] = (matched_name, f"fuzzy({score:.0f}%)")
            return matched_name, f"fuzzy({score:.0f}%)"

        # 3. 매칭 실패 → 원본 유지
        self.unmatched.append({
            "raw_name":    raw_name,
            "cleaned_name": cleaned_name,
        })
        self.cache[cleaned_name] = (cleaned_name, "unmatched")
        return cleaned_name, "unmatched"


# ------------------------------------------------------------------ #
#  파싱 함수
# ------------------------------------------------------------------ #
def clean_raw_name(raw_name: str) -> str:
    """기준 및 규격 원료명 정제"""
    name = raw_name.strip()

    # 앞 번호/기호 제거
    name = re.sub(r'^[\-\s]*[\(\s]*[\d①②③④⑤⑥⑦⑧⑨⑩]+[\)\.\s]+', '', name).strip()
    name = re.sub(r'^[\(\s]*[가나다라마바사아자차카타파하]+[\)\.\s]+', '', name).strip()
    name = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', name).strip()
    name = re.sub(r'^\-\s*', '', name).strip()

    # "총", "합" 제거
    name = re.sub(r'^[총합\s]+', '', name).strip()

    # "(-)-", "(-)" 제거
    name = re.sub(r'\(-\)-?', '', name).strip()

    # 뒤 괄호/단위 제거
    name = re.sub(r'\s*[\(\[]\s*[%a-zA-Zμ/g0-9\s]+\s*[\)\]]', '', name).strip()
    name = re.sub(r'\s*(함량|정제|추출물정)\s*$', '', name).strip()

    return name.strip()


def format_amount(amount_str: str, unit: str) -> str:
    clean = amount_str.replace(",", "").strip()
    try:
        num = int(float(clean))
    except ValueError:
        return f"{amount_str}{unit}"

    if num >= 100_000_000:
        억 = num // 100_000_000
        나머지 = num % 100_000_000
        return f"{억}억{unit}" if 나머지 == 0 else f"{억}억{나머지}{unit}"
    return f"{num}{unit}"


def parse_all_ingredients(spec_text: str, matcher: IngredientMatcher) -> list[dict]:
    results = []

    for line in spec_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = re.search(
            r'([^:：\n]+?)\s*[:：]\s*표시량[\[(]\s*([0-9,]+(?:\.[0-9]+)?)'
            r'(?:\([^)]*\))?\s*(mg|g|μg|ug|IU|CFU|%)\s*[/]',
            line,
            re.IGNORECASE
        )
        if not match:
            continue

        raw_name = match.group(1).strip()
        amount   = match.group(2).strip()
        unit     = match.group(3).strip()

        raw_name = re.sub(r'^\d+\.\s*', '', raw_name).strip()
        cleaned  = clean_raw_name(raw_name)
        final_name, method = matcher.match(cleaned, raw_name)

        results.append({
            "raw_name":  raw_name,
            "name":      final_name,
            "amount":    format_amount(amount, unit),
            "method":    method,
        })

    return results


def parse_garcinia_effect(effect_text: str) -> list[str]:
    """기능성 내용에서 가르시니아 부분만 추출"""
    GARCINIA_EFFECT_KEYWORDS = ["탄수화물이 지방으로 합성"]

    sentences = []
    lines = [l.strip() for l in effect_text.split("\n") if l.strip()]

    for line in lines:
        if "가르시니아" in line:
            colon_match = re.search(r'가르시니아[^:：\]]*[:：\]]\s*(.+)', line)
            if colon_match:
                content = colon_match.group(1).strip()
                if content:
                    parts = re.split(r'\s*[\(\（]\d+[\)\）]\s*|[①②③④⑤⑥]\s*', content)
                    sentences.extend([p.strip() for p in parts if p.strip()])
            continue

        if any(kw in line for kw in GARCINIA_EFFECT_KEYWORDS):
            content = re.sub(r'^[\(\（]\d+[\)\）]\s*|^[①②③④⑤]\s*', '', line).strip()
            if content:
                sentences.append(content)

    seen = set()
    result = []
    for s in sentences:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)

    return result


def get_product_categories(ingredients: list[dict]) -> list[int]:
    category_ids = set()
    for item in ingredients:
        cats = INGREDIENT_CATEGORY_MAP.get(item["name"], [])
        category_ids.update(cats)
    return sorted(category_ids) or [1]


def is_garcinia_product(indiv_rawmtrl_nm: str) -> bool:
    return any(kw in indiv_rawmtrl_nm for kw in GARCINIA_KEYWORDS)


# ------------------------------------------------------------------ #
#  Management Command
# ------------------------------------------------------------------ #
class Command(BaseCommand):
    help = "API 데이터를 퍼지매칭으로 정제하여 CSV로 저장합니다"

    def handle(self, *args, **options):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 퍼지매처 초기화
        self.stdout.write("퍼지매처 초기화 중...")
        matcher = IngredientMatcher(self.stdout)

        # CSV 파일 열기
        products_file = open(
            os.path.join(OUTPUT_DIR, "products.csv"), "w",
            newline="", encoding="utf-8-sig"
        )
        pi_file = open(
            os.path.join(OUTPUT_DIR, "product_ingredients.csv"), "w",
            newline="", encoding="utf-8-sig"
        )
        ing_file = open(
            os.path.join(OUTPUT_DIR, "ingredients.csv"), "w",
            newline="", encoding="utf-8-sig"
        )

        products_writer = csv.writer(products_file)
        pi_writer       = csv.writer(pi_file)
        ing_writer      = csv.writer(ing_file)

        products_writer.writerow(["name", "company", "productType", "category_ids"])
        pi_writer.writerow(["product_name", "ingredient_name", "amount", "raw_name", "match_method"])
        ing_writer.writerow(["name", "effect"])

        seen_ingredients = {}
        seen_products    = set()
        garcinia_effect  = []
        product_count    = 0
        start = 1
        total = None

        while True:
            end = start + BATCH_SIZE - 1
            url = f"{BASE_URL}/{start}/{end}"
            self.stdout.write(f"\nAPI 요청: {start}~{end}번째...")

            try:
                resp = requests.get(url, timeout=30)
                root = ET.fromstring(resp.content)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ 요청 실패: {e}"))
                break

            if total is None:
                total_el = root.find("total_count")
                total = int(total_el.text) if total_el is not None else 0
                self.stdout.write(f"전체 데이터: {total:,}개")

            rows = root.findall("row")
            if not rows:
                break

            for row in rows:
                indiv_rawmtrl_nm = row.findtext("INDIV_RAWMTRL_NM") or ""
                if not is_garcinia_product(indiv_rawmtrl_nm):
                    continue

                name    = row.findtext("PRDLST_NM") or ""
                company = row.findtext("BSSH_NM") or ""
                effect  = row.findtext("PRIMARY_FNCLTY") or ""
                spec    = row.findtext("STDR_STND") or ""

                if not name or name in seen_products:
                    continue

                seen_products.add(name)

                # 가르시니아 effect (최초 1회)
                if not garcinia_effect and "가르시니아" in effect:
                    garcinia_effect = parse_garcinia_effect(effect)

                # 기준 및 규격 파싱 (퍼지매칭 포함)
                parsed = parse_all_ingredients(spec, matcher) if spec else []

                # 카테고리
                category_ids = get_product_categories(parsed)

                # products.csv
                products_writer.writerow([
                    name, company, "건강기능식품",
                    ";".join(map(str, category_ids))
                ])

                # product_ingredients.csv
                for item in parsed:
                    pi_writer.writerow([
                        name,
                        item["name"],
                        item["amount"],
                        item["raw_name"],
                        item["method"],
                    ])

                    # ingredients.csv (최초 1회)
                    if item["name"] not in seen_ingredients:
                        effect_val = (
                            "|".join(garcinia_effect)
                            if item["name"] == "가르시니아캄보지아 추출물"
                            else ""
                        )
                        seen_ingredients[item["name"]] = True
                        ing_writer.writerow([item["name"], effect_val])

                product_count += 1

            self.stdout.write(f"  → 수집된 제품: {product_count}개")

            start += BATCH_SIZE
            if start > total:
                break

            time.sleep(1)

        products_file.close()
        pi_file.close()
        ing_file.close()

        # 매칭 실패 목록 저장
        if matcher.unmatched:
            unmatched_path = os.path.join(OUTPUT_DIR, "unmatched_ingredients.csv")
            with open(unmatched_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["raw_name", "cleaned_name"])
                for item in matcher.unmatched:
                    writer.writerow([item["raw_name"], item["cleaned_name"]])
            self.stdout.write(self.style.WARNING(
                f"\n⚠ 매칭 실패: {len(matcher.unmatched)}개 → {unmatched_path} 확인 필요"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\n완료! CSV 저장됨:\n"
            f"  data/products.csv ({product_count}개 제품)\n"
            f"  data/product_ingredients.csv\n"
            f"  data/ingredients.csv\n\n"
            f"CSV 검증 후:\n"
            f"  python manage.py import_garcinia_from_csv --dry-run\n"
            f"  python manage.py import_garcinia_from_csv"
        ))