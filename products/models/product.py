from django.db import models
from django.utils import timezone

from users.models import User


class Product(models.Model):
    name = models.TextField(verbose_name="제품 이름")
    company = models.TextField(verbose_name="회사 이름")
    productType = models.TextField(verbose_name="식품의 유형")
    viewCount = models.IntegerField(verbose_name="조회수", default=0)
    coupang = models.TextField(verbose_name="쿠팡 링크", null=True, blank=True)

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

class ProductRequest(models.Model):
    content = models.TextField(verbose_name="제품 정보")

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_requests",
        verbose_name="요청한 사용자"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_requests"

    def __str__(self):
        return f"제품 요청 #{self.id}"