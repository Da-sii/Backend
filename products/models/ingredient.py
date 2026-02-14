from django.db import models

class Ingredient(models.Model):
    name = models.TextField(verbose_name="성분 이름")
    mainIngredient = models.TextField(max_length=100, verbose_name="주성분이름", null=True, blank=True)
    minRecommended = models.CharField(max_length=50, verbose_name="최소권장량", null=True, blank=True)
    maxRecommended = models.CharField(max_length=50, verbose_name="최대권장량", null=True, blank=True)
    effect = models.JSONField(default=list, verbose_name="효과", null=True, blank=True)
    sideEffect = models.JSONField(default=list, verbose_name="부작용", null=True, blank=True)

    class Meta:
        db_table = "ingredients"

    def __str__(self):
        return self.name

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
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="기타 원료명"
    )

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