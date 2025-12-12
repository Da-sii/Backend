from django.db import migrations

def convert_effect_sideeffect_to_json(apps, schema_editor):
    Ingredient = apps.get_model("products", "Ingredient")

    for ing in Ingredient.objects.all():
        # 문자열이 들어있을 가능성이 있으므로 안전하게 처리
        effect = ing.effect or ""
        side = ing.sideEffect or ""

        # 줄바꿈 기준으로 배열 변환
        def normalize(value):
            if not value:
                return []
            # 문자열일 경우만 분해
            if isinstance(value, str):
                return [
                    line.strip()
                    for line in value.split("\n")
                    if line.strip()
                ]
            return value  # 이미 리스트면 그대로 사용

        ing.effect = normalize(effect)
        ing.sideEffect = normalize(side)
        ing.save()

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0019_alter_ingredient_effect_alter_ingredient_sideeffect'),
    ]

    operations = [
        migrations.RunPython(convert_effect_sideeffect_to_json)
    ]
