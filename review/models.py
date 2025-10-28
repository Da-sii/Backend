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
    updated = models.BooleanField(default=False, verbose_name="수정여부")

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
        
class ReviewReportReason(models.TextChoices):
    IRRELEVANT = "IRRELEVANT", "제품과 관련 없는 이미지 / 내용"
    MISMATCH = "MISMATCH", "제품 미사용 / 리뷰 내용과 다른 제품 선택"
    PROMOTION = "PROMOTION", "광고 홍보 / 거래 시도"
    ABUSE = "ABUSE", "욕설, 비속어가 포함된 내용"
    PRIVACY = "PRIVACY", "개인 정보 노출"


class ReviewReport(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name="리뷰 아이디"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_reports",
        verbose_name="신고자 아이디"
    )
    reason = models.CharField(
        max_length=32,
        choices=ReviewReportReason.choices,
        verbose_name="신고 사유"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="신고 일시")

    class Meta:
        db_table = "reviewReports"
        constraints = [
            models.UniqueConstraint(fields=["review", "reporter"], name="unique_review_report_per_user")
        ]

    def __str__(self):
        return f"Report {self.id} - Review {self.review.id} by {self.reporter_id} ({self.reason})"


class BlockedReview(models.Model):
    """
    신고된 리뷰를 차단하는 모델
    JWT에서 파싱한 userId와 차단된 reviewId를 저장
    """
    user_id = models.IntegerField(verbose_name="차단한 사용자 ID")
    blocked_review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
        verbose_name="차단된 리뷰"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="차단 일시")

    class Meta:
        db_table = "blocked_reviews"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "blocked_review"], name="unique_blocked_review_per_user")
        ]

    def __str__(self):
        return f"User {self.user_id} blocked Review {self.blocked_review.id}"


class BlockedUser(models.Model):
    """
    사용자 차단 모델
    차단한 사용자와 차단당한 사용자의 관계를 저장
    """
    blocker_user_id = models.IntegerField(verbose_name="차단한 사용자 ID")
    blocked_user_id = models.IntegerField(verbose_name="차단당한 사용자 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="차단 일시")

    class Meta:
        db_table = "blocked_users"
        constraints = [
            models.UniqueConstraint(fields=["blocker_user_id", "blocked_user_id"], name="unique_blocked_user_relationship")
        ]

    def __str__(self):
        return f"User {self.blocker_user_id} blocked User {self.blocked_user_id}"