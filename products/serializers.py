from typing import List, Dict, Any

from django.db import transaction
from rest_framework import serializers

from products.models import Product, ProductImage, Ingredient, ProductIngredient


class ProductIngredientInputSerializer(serializers.Serializer):
    ingredientId = serializers.IntegerField()
    amount = serializers.IntegerField()


class ProductCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.URLField(max_length=500), required=False, allow_empty=True
    )
    ingredients = ProductIngredientInputSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = (
            "name",
            "company",
            "price",
            "unit",
            "piece",
            "nutrients",
            "viewCount",
            "images",
            "ingredients",
        )

    def validate_ingredients(self, value: List[Dict[str, Any]]):
        if not value:
            return value

        ingredient_ids = [item.get("ingredientId") for item in value]

        if None in ingredient_ids:
            raise serializers.ValidationError("ingredientId는 필수입니다.")

        existing = set(
            Ingredient.objects.filter(id__in=ingredient_ids).values_list("id", flat=True)
        )

        missing = [i for i in ingredient_ids if i not in existing]

        if missing:
            raise serializers.ValidationError(f"존재하지 않는 성분 ID: {missing}")

        for item in value:
            amount = item.get("amount")

            if amount is None or amount < 0:
                raise serializers.ValidationError("amount는 0 이상이어야 합니다.")

        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        # viewCount 기본값 0 처리
        if attrs.get("viewCount") is None:
            attrs["viewCount"] = 0
            
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Product:
        images: List[str] = validated_data.pop("images", [])
        ingredients_input: List[Dict[str, Any]] = validated_data.pop("ingredients", [])

        product = Product.objects.create(**validated_data)

        if images:
            ProductImage.objects.bulk_create(
                [ProductImage(product=product, url=url) for url in images]
            )

        if ingredients_input:
            # 미리 Ingredient 객체 맵 구성
            ingredient_id_to_obj = {
                ing.id: ing for ing in Ingredient.objects.filter(
                    id__in=[item["ingredientId"] for item in ingredients_input]
                )
            }
            ProductIngredient.objects.bulk_create(
                [
                    ProductIngredient(
                        product=product,
                        ingredient=ingredient_id_to_obj[item["ingredientId"]],
                        amount=item["amount"],
                    )
                    for item in ingredients_input
                ]
            )

        return product


