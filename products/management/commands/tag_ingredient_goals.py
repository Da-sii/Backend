import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from google import genai
from google.genai import types

from products.models import Ingredient
from recommendations.constants import GOAL_CHOICES

BATCH_SIZE = 50
OUTPUT_PATH = Path(settings.BASE_DIR) / "ingredient_goals_review.json"

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _classify_batch(batch: list) -> dict:
    prompt = f"""당신은 건강기능식품 성분 분류 전문가입니다.

아래는 분류할 성분 목록입니다:
{json.dumps(batch, ensure_ascii=False)}

아래 목표(goal) 중 각 성분에 해당하는 것을 모두 고르세요 (복수 선택 가능, 해당 없으면 빈 리스트):
{json.dumps(GOAL_CHOICES, ensure_ascii=False)}

판단 기준: 성분의 effect(효과)를 우선 근거로 삼으세요.

아래 JSON 형식으로만, 입력받은 모든 성분에 대해 빠짐없이 응답하세요:
{{
  "results": [
    {{"id": 성분 ID (정수), "goals": ["해당 목표", ...]}}
  ]
}}"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            result = json.loads(response.text)
            return {r["id"]: r["goals"] for r in result["results"]}
        except Exception as e:
            if attempt == 2:
                raise
            wait = 5 * (attempt + 1)
            print(f"  ⚠ 배치 실패 ({e}), {wait}초 후 재시도...")
            time.sleep(wait)


class Command(BaseCommand):
    help = "Ingredient.goals 필드를 Gemini로 분류합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help=f"분류 없이 {OUTPUT_PATH.name} 파일을 읽어 DB에 반영합니다.",
        )

    def handle(self, *args, **options):
        if options["apply"]:
            self._apply()
        else:
            self._dry_run()

    def _dry_run(self):
        ingredients = list(
            Ingredient.objects.exclude(effect=[]).exclude(effect__isnull=True)
            .values("id", "name", "effect", "sideEffect")
        )
        self.stdout.write(f"대상 성분 {len(ingredients)}개, 배치 크기 {BATCH_SIZE}")

        goals_by_id = {}
        batches = list(_chunks(ingredients, BATCH_SIZE))
        for idx, batch in enumerate(batches, 1):
            self.stdout.write(f"  배치 {idx}/{len(batches)} 처리 중...")
            goals_by_id.update(_classify_batch(batch))
            if idx < len(batches):
                time.sleep(2)

        review = []
        goal_counts = {g: 0 for g in GOAL_CHOICES}
        empty = []
        for ing in ingredients:
            goals = goals_by_id.get(ing["id"], [])
            review.append({
                "id": ing["id"],
                "name": ing["name"],
                "effect": ing["effect"],
                "sideEffect": ing["sideEffect"],
                "goals": goals,
            })
            for g in goals:
                if g in goal_counts:
                    goal_counts[g] += 1
            if not goals:
                empty.append(ing["name"])

        OUTPUT_PATH.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"\n{OUTPUT_PATH} 에 저장 완료"))
        self.stdout.write("목표별 개수:")
        for g, c in goal_counts.items():
            self.stdout.write(f"  {g}: {c}")
        self.stdout.write(
            f"goals 없음 ({len(empty)}개): "
            f"{', '.join(empty[:20])}{' ...' if len(empty) > 20 else ''}"
        )
        self.stdout.write(self.style.WARNING("\n검수 후 --apply 로 DB에 반영하세요."))

    def _apply(self):
        if not OUTPUT_PATH.exists():
            self.stderr.write(self.style.ERROR(f"{OUTPUT_PATH} 없음. 먼저 dry-run(옵션 없이) 실행하세요."))
            return

        review = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        updated = 0
        for item in review:
            updated += Ingredient.objects.filter(id=item["id"]).update(goals=item["goals"])

        self.stdout.write(self.style.SUCCESS(f"{updated}개 성분 goals 반영 완료"))
