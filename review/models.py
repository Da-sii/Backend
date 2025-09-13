from django.db import models
from django.conf import settings
from products.models import Product

class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="유저 아이디"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="프로덕트 아이디"
    )
    rate = models.IntegerField(verbose_name="별점")
    review = models.TextField(verbose_name="리뷰")
    date = models.DateField(auto_now_add=True, verbose_name="최종날짜")

    class Meta:
        db_table = "reviews"

    def __str__(self):
        return f"Review {self.id} - {self.user.email} - {self.product.name}"

class ReviewImage(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="리뷰 아이디"
    )
    url = models.URLField(verbose_name="이미지 URL")

    class Meta:
        db_table = "reviewImages"

    def __str__(self):
        return f"Image {self.id} - Review {self.review.id}"
