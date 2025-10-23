from django.db import models
from django.utils import timezone
class BigCategory(models.Model):
    category = models.CharField(max_length=100, verbose_name="카테고리")

    class Meta:
        db_table = "big_categories"

    def __str__(self):
        return self.category

class SmallCategory(models.Model):
    bigCategory = models.ForeignKey(
        BigCategory,
        on_delete=models.CASCADE,
        related_name="smallCategories",
        verbose_name="대분류 외래키",
    )
    category = models.CharField(max_length=100, verbose_name="카테고리")

    class Meta:
        db_table = "small_categories"

    def __str__(self):
        return f"{self.bigCategory.category} - {self.category}"

class Product(models.Model):
    name = models.TextField(verbose_name="제품 이름")
    company = models.TextField(verbose_name="회사 이름")
    price = models.IntegerField(verbose_name="가격")
    unit = models.TextField(verbose_name="단위")
    piece = models.TextField(verbose_name="개수")
    productType = models.TextField(verbose_name="식품의 유형")
    viewCount = models.IntegerField(verbose_name="조회수", default=0)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name

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
class CategoryProduct(models.Model):
    category = models.ForeignKey(
        SmallCategory,
        on_delete=models.PROTECT, # 카테고리 삭제 방지
        related_name="category_products",
        verbose_name="카테고리 외래키",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT, # 제품 삭제 방지,
        related_name="category_products",
        verbose_name="제품 외래키",
    )

    class Meta:
        db_table = "category_products"

    def __str__(self):
        return f"{self.category.category} - {self.product.name}"

class ProductDailyView(models.Model):
    product = models.ForeignKey("Product", on_delete=models.CASCADE, related_name="daily_views")
    date = models.DateField(default=timezone.now)
    views = models.IntegerField(default=0)

    class Meta:
        db_table = "product_daily_views"
        unique_together = ("product", "date")  # 하루에 한 행만
        indexes = [
            models.Index(fields=["date"]),                 # 날짜 검색 빠르게
            models.Index(fields=["product", "date"]),      # 제품별 날짜 검색 빠르게
        ]

    def __str__(self):
        return f"{self.product.name} - {self.date} - {self.views}"

class Ingredient(models.Model):
    name = models.TextField(verbose_name="성분 이름")
    englishIngredient = models.CharField(max_length=100, verbose_name="영어이름")
    minRecommended = models.CharField(max_length=50, verbose_name="최소권장량")
    maxRecommended = models.CharField(max_length=50, verbose_name="최대권장량")
    effect = models.TextField(verbose_name="효과")
    sideEffect = models.TextField(verbose_name="부작용", null=True, blank=True)

    class Meta:
        db_table = "ingredients"

    def __str__(self):
        return self.name

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
    amount = models.CharField(max_length=50, verbose_name="포함량")

    class Meta:
        db_table = "product_ingredients"

    def __str__(self):
        return f"{self.product.name} - {self.ingredient.name} ({self.amount})"