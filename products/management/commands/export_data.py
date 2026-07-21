import json
from pathlib import Path

from django.core.management.base import BaseCommand

from products.models import Ingredient, Product


class Command(BaseCommand):
    help = "Ingredient/Product 데이터를 ingredients_export.json, products_export.json으로 export합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=".",
            help="JSON 파일을 저장할 디렉토리 (기본값: 현재 디렉토리)",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        ingredients = list(
            Ingredient.objects.values(
                "id",
                "name",
                "mainIngredient",
                "effect",
                "sideEffect",
                "minRecommended",
                "maxRecommended",
            )
        )
        ingredients_path = output_dir / "ingredients_export.json"
        with ingredients_path.open("w", encoding="utf-8") as f:
            json.dump(ingredients, f, ensure_ascii=False, indent=2)
        self.stdout.write(
            self.style.SUCCESS(f"{ingredients_path} 저장 완료 ({len(ingredients)}건)")
        )

        products = []
        queryset = Product.objects.prefetch_related("ingredients__ingredient")
        for product in queryset:
            products.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "company": product.company,
                    "ingredients": [
                        {
                            "ingredient_id": pi.ingredient_id,
                            "ingredient_name": pi.ingredient.name,
                            "amount": pi.amount,
                        }
                        for pi in product.ingredients.all()
                    ],
                }
            )
        products_path = output_dir / "products_export.json"
        with products_path.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        self.stdout.write(
            self.style.SUCCESS(f"{products_path} 저장 완료 ({len(products)}건)")
        )
