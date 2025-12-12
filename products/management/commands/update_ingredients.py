from django.core.management.base import BaseCommand
from products.api.import_ingredients import update_ingredients_from_openapi

class Command(BaseCommand):
    help = "식약처 OpenAPI로부터 성분 데이터를 업데이트합니다."

    def handle(self, *args, **options):
        update_ingredients_from_openapi()
        self.stdout.write(self.style.SUCCESS("Ingredient 업데이트 완료"))