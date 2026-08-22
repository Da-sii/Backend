from django.db import transaction
from rest_framework import serializers

from products.models import Ingredient
from recommendations.models import SavedRecommendation, SavedRecommendationItem


class SaveItemSerializer(serializers.Serializer):
    """저장 요청에 담기는 성분 1개"""

    ingredient_id = serializers.IntegerField()
    intro = serializers.CharField()
    reason = serializers.CharField()
    fit_score = serializers.IntegerField(min_value=0, max_value=100)

    def validate_ingredient_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError("존재하지 않는 성분입니다.")

        return value

class SaveRecommendationSerializer(serializers.Serializer):
    """저장하기 요청 본문 - 유저당 1건, 기존건 교체"""

    items = SaveItemSerializer(many=True, min_length=1, max_length=3)

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        items = validated_data['items']

        recommendation, _ = SavedRecommendation.objects.get_or_create(user=user)
        recommendation.items.all().delete()
        recommendation.save() # updated_at 갱신

        SavedRecommendationItem.objects.bulk_create([
            SavedRecommendationItem(
                recommendation=recommendation,
                ingredient_id=item["ingredient_id"],
                intro=item["intro"],
                reason=item["reason"],
                fit_score=item["fit_score"],
                rank=idx,
            )
            for idx, item in enumerate(items, start=1)
        ])

        return recommendation

class SavedItemSerializer(serializers.ModelSerializer):
    """저장된 성분 1개 조회용"""

    ingredient_id = serializers.IntegerField(source="ingredient.id", read_only=True)
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = SavedRecommendationItem
        fields = ["ingredient_id", "ingredient_name", "intro", "reason", "fit_score", "rank"]

class SavedRecommendationSerializer(serializers.ModelSerializer):
    """저장된 추천 조회용"""

    items = SavedItemSerializer(many=True, read_only=True)

    class Meta:
        model = SavedRecommendation
        fields = ["id", "created_at", "updated_at", "items"]