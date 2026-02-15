from rest_framework import serializers

from products.models import IngredientGuide


class GuideListSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name")

    class Meta:
        model = IngredientGuide
        fields = ("id", "ingredient_name")