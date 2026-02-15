from rest_framework import serializers

from products.models import IngredientGuide


class GuideListSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name")

    class Meta:
        model = IngredientGuide
        fields = ("id", "ingredient_name")

class MainRandomGuideSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="ingredient.name")

    class Meta:
        model = IngredientGuide
        fields = ("id", "name")

class GuideDetailSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.CharField(source="ingredient.id")
    name = serializers.CharField(source="ingredient.name")
    mainIngredients = serializers.CharField(source="ingredient.mainIngredient")
    productCount = serializers.SerializerMethodField()

    class Meta:
        model = IngredientGuide
        fields = ("id", "ingredient_id", "name", "mainIngredients", "keyPoints", "sources", "productCount")

    def get_productCount(self, obj):
        return obj.ingredient.productIngredients.count()