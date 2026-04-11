"""
products/management/commands/import_garcinia_from_csv.py

CSV 파일을 검증 후 DB에 삽입합니다.
crawl_garcinia_to_csv 커맨드로 먼저 CSV를 생성하세요.

사용법:
    python manage.py import_garcinia_from_csv --dry-run  # 검증만
    python manage.py import_garcinia_from_csv            # 실제 저장
"""

import csv
import os

from django.core.management.base import BaseCommand
from products.models import (
    Ingredient, Product, ProductIngredient,
    CategoryProduct, SmallCategory
)

OUTPUT_DIR = "data"


class Command(BaseCommand):
    help = "CSV 파일을 DB에 삽입합니다"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB 저장 없이 검증만 수행"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN 모드 — DB에 저장하지 않습니다\n"))

        products_path            = os.path.join(OUTPUT_DIR, "products.csv")
        product_ingredients_path = os.path.join(OUTPUT_DIR, "product_ingredients.csv")
        ingredients_path         = os.path.join(OUTPUT_DIR, "ingredients.csv")

        for path in [products_path, product_ingredients_path, ingredients_path]:
            if not os.path.exists(path):
                self.stdout.write(self.style.ERROR(f"파일 없음: {path}"))
                return

        # ── 1단계: ingredients.csv → Ingredient 저장 ─────────────── #
        self.stdout.write("1단계: Ingredient 저장 중...")
        ing_success, ing_skip = 0, 0

        with open(ingredients_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name   = row["name"].strip()
                effect = row["effect"].strip()

                if not name:
                    continue

                effect_list = [e.strip() for e in effect.split("|") if e.strip()]
                defaults = {"effect": effect_list, "sideEffect": []}

                if name == "가르시니아캄보지아 추출물":
                    defaults.update({
                        "mainIngredient": "Hydroxycitric acid (HCA)",
                        "minRecommended": "750mg",
                        "maxRecommended": "2800mg",
                    })

                if not dry_run:
                    _, created = Ingredient.objects.get_or_create(
                        name=name, defaults=defaults
                    )
                    if created:
                        ing_success += 1
                    else:
                        ing_skip += 1
                else:
                    self.stdout.write(f"  [DRY] Ingredient: {name} | effect: {effect_list}")
                    ing_success += 1

        self.stdout.write(f"  → 생성: {ing_success} / 이미 존재: {ing_skip}\n")

        # ── 2단계: products.csv → Product + CategoryProduct 저장 ─── #
        self.stdout.write("2단계: Product + CategoryProduct 저장 중...")
        prod_success, prod_skip, cat_success = 0, 0, 0

        with open(products_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name         = row["name"].strip()
                company      = row["company"].strip()
                product_type = row["productType"].strip()
                category_ids = [
                    int(c) for c in row["category_ids"].split(";")
                    if c.strip().isdigit()
                ]

                if not name:
                    continue

                if not dry_run:
                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            "company":     company,
                            "productType": product_type,
                        }
                    )
                    if created:
                        prod_success += 1
                    else:
                        prod_skip += 1

                    for cat_id in category_ids:
                        try:
                            category = SmallCategory.objects.get(id=cat_id)
                            _, cat_created = CategoryProduct.objects.get_or_create(
                                product=product,
                                category=category,
                            )
                            if cat_created:
                                cat_success += 1
                        except SmallCategory.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠ SmallCategory id={cat_id} 없음")
                            )
                else:
                    self.stdout.write(
                        f"  [DRY] Product: {name} | 카테고리: {category_ids}"
                    )
                    prod_success += 1

        self.stdout.write(
            f"  → 제품 생성: {prod_success} / 이미 존재: {prod_skip} / "
            f"카테고리 연결: {cat_success}\n"
        )

        # ── 3단계: product_ingredients.csv → ProductIngredient 저장 ─ #
        self.stdout.write("3단계: ProductIngredient 저장 중...")
        pi_success, pi_fail = 0, 0

        with open(product_ingredients_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                product_name    = row["product_name"].strip()
                ingredient_name = row["ingredient_name"].strip()
                amount          = row["amount"].strip()

                if not product_name or not ingredient_name:
                    continue

                if not dry_run:
                    try:
                        product    = Product.objects.get(name=product_name)
                        ingredient = Ingredient.objects.get(name=ingredient_name)
                        ProductIngredient.objects.get_or_create(
                            product=product,
                            ingredient=ingredient,
                            defaults={"amount": amount}
                        )
                        pi_success += 1
                    except Product.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Product 없음: {product_name}")
                        )
                        pi_fail += 1
                    except Ingredient.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠ Ingredient 없음: {ingredient_name} "
                                f"(원본: {row.get('raw_name', '')})"
                            )
                        )
                        pi_fail += 1
                else:
                    self.stdout.write(
                        f"  [DRY] {product_name} → {ingredient_name} ({amount}) "
                        f"[{row.get('match_method', '')}]"
                    )
                    pi_success += 1

        self.stdout.write(f"  → 저장: {pi_success} / 실패: {pi_fail}\n")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN 완료 — 실제 저장하려면 --dry-run 없이 실행하세요"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("DB 삽입 완료!"))