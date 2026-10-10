from django.db import models

class Ingredient(models.Model):
    name = models.TextField(verbose_name="성분 이름")
    mainIngredient = models.TextField(max_length=100, verbose_name="주성분이름", null=True, blank=True)
    minRecommended = models.CharField(max_length=50, verbose_name="최소권장량", null=True, blank=True)
    maxRecommended = models.CharField(max_length=50, verbose_name="최대권장량", null=True, blank=True)
    effect = models.JSONField(default=list, verbose_name="효과", null=True, blank=True)
    sideEffect = models.JSONField(default=list, verbose_name="부작용", null=True, blank=True)
    goals = models.JSONField(default=list, verbose_name="추천 목표", blank=True)
    hashtags = models.JSONField(default=list, verbose_name="해시태그", blank=True)

    class Meta:
        db_table = "ingredients"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # 해시태그는 공백 제거 후 저장 (띄어쓰기 무시 검색용), 빈 값·중복 제거
        # 주의: QuerySet.update(), bulk_create(), bulk_update(), raw SQL은 save()를 호출하지 않아
        #       정규화가 적용되지 않음 → hashtags를 저장할 때는 반드시 save()(또는 create()) 사용
        hashtags = []
        for tag in self.hashtags or []:
            tag = "".join(str(tag).split()).lstrip("#")
            if tag and tag not in hashtags:
                hashtags.append(tag)
        self.hashtags = hashtags
        super().save(*args, **kwargs)

class ProductIngredient(models.Model):
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE, # 제품 삭제 -> 연결 관계도 삭제
        related_name="ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT, # 성분은 삭제 방지
        related_name="productIngredients",
    )
    amount = models.CharField(max_length=50, verbose_name="포함량")

    class Meta:
        db_table = "product_ingredients"

    def __str__(self):
        return f"{self.product.name} - {self.ingredient.name} ({self.amount})"

class OtherIngredient(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="기타 원료명")

    class Meta:
        db_table = "other_ingredients"

    def __str__(self):
        return self.name

class ProductOtherIngredient(models.Model):
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="product_other_ingredients",
        verbose_name="제품"
    )
    other_ingredient = models.ForeignKey(
        OtherIngredient,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="기타 원료"
    )

    class Meta:
        db_table = "product_other_ingredients"
        unique_together = ("product", "other_ingredient")
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["other_ingredient"]),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.other_ingredient.name}"

class IngredientGuide(models.Model):
    ingredient = models.OneToOneField(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="guide",
    )

    keyPoints = models.JSONField(default=list, verbose_name="핵심 포인트", blank=True)
    sources = models.JSONField(default=list, verbose_name="출처", blank=True)

    class Meta:
        db_table = "ingredient_guides"