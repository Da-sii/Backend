from django.db import models

class Product(models.Model):
    name = models.TextField(verbose_name="제품 이름")
    company = models.TextField(verbose_name="회사 이름")
    price = models.IntegerField(verbose_name="가격")
    unit = models.TextField(verbose_name="단위")
    piece = models.IntegerField(verbose_name="개수")
    nutrients = models.TextField(verbose_name="영양정보")
    viewCount = models.IntegerField(verbose_name="조회수")

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.product

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",)
    url = models.URLField(
        max_length=500,
        verbose_name="이미지 URL"
    )

    class Meta:
        db_table = "product_images"

    def __str__(self):
        return f"{self.product.name} 이미지"

class Ingredient(models.Model):
    name = models.TextField(verbose_name="성분 이름")
    englishIngredient = models.CharField(verbose_name="영어이름")
    minRecommended = models.IntegerField(verbose_name="최소권장량")
    maxRecommended = models.IntegerField(verbose_name="최대권장량")
    effect = models.TextField(verbose_name="효과")
    sideEffect = models.TextField(verbose_name="부작용")

    class Meta:
        db_table = "ingredients"

    def __str__(self):
        return self.ingredient

class ProductIngredient(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE, # 제품 삭제 -> 연결 관계도 삭제
        related_name="ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT, # 성분은 삭제 방지
        related_name="productIngredients",
    )
    amount = models.IntegerField(verbose_name="포함량")

    class Meta:
        db_table = "productIngredients"

    def __str__(self):
        return f"{self.product.product} - {self.ingredient.ingredient} ({self.amount})"