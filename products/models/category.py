from django.db import models


class BigCategory(models.Model):
    category = models.CharField(max_length=100, verbose_name="카테고리")

    class Meta:
        db_table = "big_categories"

    def __str__(self):
        return self.category

class MiddleCategory(models.Model):
    category = models.CharField(max_length=100, verbose_name="카테고리")

    big_category = models.ForeignKey(
        BigCategory,
        on_delete=models.CASCADE,
        related_name="middle_categories",
        verbose_name="대분류 외래키",
    )

    class Meta:
        db_table = "middle_categories"

class SmallCategory(models.Model):
    category = models.CharField(max_length=100, verbose_name="카테고리")

    middle_category = models.ForeignKey(
        MiddleCategory,
        on_delete=models.CASCADE,
        related_name="small_categories",
        verbose_name="중분류 외래키",
    )

    class Meta:
        db_table = "small_categories"

    def __str__(self):
        return f"{self.middle_category.big_category.category} - {self.middle_category.category} - {self.category}"

class CategoryProduct(models.Model):
    category = models.ForeignKey(
        SmallCategory,
        on_delete=models.PROTECT, # 카테고리 삭제 방지
        related_name="category_products",
        verbose_name="카테고리 외래키",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT, # 제품 삭제 방지,
        related_name="category_products",
        verbose_name="제품 외래키",
    )

    class Meta:
        db_table = "category_products"

    def __str__(self):
        return f"{self.category.category} - {self.product.name}"