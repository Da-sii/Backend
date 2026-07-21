from django.db import models

from products.models import Ingredient
from users.models import User


class UserSurvey(models.Model):
    """유저당 1개, 최신 설문 보관"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="survey",
        verbose_name="응답 사용자",
    )
    answers = models.JSONField(verbose_name="설문 응답")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_surveys"

    def __str__(self):
        return f"{self.user.email}의 설문"


class SavedRecommendation(models.Model):
    """추천 결과 저장(유저 당 1건, 재저장 시 교체)"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="saved_recommendations",
        verbose_name="저장한 사용자",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_recommendations"

    def __str__(self):
        return f"{self.user.email}의 저장된 추천"


class SavedRecommendationItem(models.Model):
    """저장된 추천에 포함된 성분 1개 (건당 3개)"""

    recommendation = models.ForeignKey(
        SavedRecommendation,
        on_delete=models.CASCADE,
        related_name="items",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,  # 성분 삭제 방지
        related_name="saved_recommendation_items",
    )
    intro = models.TextField(verbose_name="성분 한 줄 소개")
    reason = models.TextField(verbose_name="추천 이유")
    fit_score = models.IntegerField(verbose_name="적합도")
    rank = models.IntegerField(verbose_name="추천 순위")

    class Meta:
        db_table = "saved_recommendation_items"
        ordering = ["rank"]
        unique_together = ("recommendation", "rank")

    def __str__(self):
        return f"{self.recommendation_id} - {self.rank}위 {self.ingredient.name}"
