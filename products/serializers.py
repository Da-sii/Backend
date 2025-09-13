import json, boto3, uuid
from typing import List, Dict, Any
from django.db import transaction
from rest_framework import serializers
from django.conf import settings

from products.models import Product, ProductImage, Ingredient, ProductIngredient

class ProductIngredientInputSerializer(serializers.Serializer):
    ingredientId = serializers.IntegerField()
    amount = serializers.CharField()
class ProductCreateSerializer(serializers.ModelSerializer):
    # 여러 이미지 파일
    images = serializers.ListField(
        child=serializers.ImageField(), required=False, allow_empty=True
    )
    # 문자열(JSON)로 받음
    ingredients = serializers.CharField(required=False)

    class Meta:
        model = Product
        fields = ("name", "company", "price", "unit", "piece", "productType", "images", "ingredients")

    def validate_ingredients(self, value: str) -> List[Dict[str, Any]]:
        if not value:
            return []

        try:
            data = json.loads(value)  # 문자열 → JSON 변환
        except json.JSONDecodeError:
            raise serializers.ValidationError("ingredients는 JSON 형식이어야 합니다.")

        if not isinstance(data, list):
            raise serializers.ValidationError("ingredients는 배열이어야 합니다.")

        return data

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Product:
        images: List[str] = validated_data.pop("images", [])
        ingredients_input: List[Dict[str, Any]] = validated_data.pop("ingredients", [])
        product = Product.objects.create(**validated_data)

        # --- S3 업로드 ---
        if images:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            uploaded_images = []
            for img in images:
                filename = f"products/{uuid.uuid4()}_{img.name}"
                s3.upload_fileobj(
                    img,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    filename,
                    ExtraArgs={"ContentType": img.content_type},
                )
                url = f"{settings.CLOUDFRONT_DOMAIN}/{filename}"
                uploaded_images.append(ProductImage(product=product, url=url))

            ProductImage.objects.bulk_create(uploaded_images)

        # --- Ingredients 저장 ---
        if ingredients_input:
            ingredient_id_to_obj = {
                ing.id: ing
                for ing in Ingredient.objects.filter(
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
class ProductIngredientReadSerializer(serializers.ModelSerializer):
    ingredientName = serializers.CharField(source="ingredient.name")

    class Meta:
        model = ProductIngredient
        fields = ("ingredientName", "amount")

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("url",)

class ProductReadSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    ingredients = ProductIngredientReadSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "company", "price", "unit", "piece", "productType", "images", "ingredients")

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("url",)

class ProductIngredientDetailSerializer(serializers.ModelSerializer):
    ingredientName = serializers.CharField(source="ingredient.name")
    englishName = serializers.CharField(source="ingredient.englishIngredient")
    minRecommended = serializers.CharField(source="ingredient.minRecommended")
    maxRecommended = serializers.CharField(source="ingredient.maxRecommended")
    effect = serializers.CharField(source="ingredient.effect")
    sideEffect = serializers.CharField(source="ingredient.sideEffect")
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProductIngredient
        fields = ("ingredientName", "englishName", "amount", "minRecommended", "maxRecommended", "effect", "sideEffect", "status")

    def get_status(self, obj: ProductIngredient) -> str:
        try:
            # 문자열에서 숫자만 추출 (예: "750mg" -> 750)
            amount_value = float("".join([c for c in obj.amount if c.isdigit() or c == "."]))
            min_value = float("".join([c for c in obj.ingredient.minRecommended if c.isdigit() or c == "."]))
            max_value = float("".join([c for c in obj.ingredient.maxRecommended if c.isdigit() or c == "."]))
        except Exception:
            return "unknown"

        if amount_value < min_value:
            return "미만"
        elif amount_value > max_value:
            return "초과"
        else:
            return "적정"

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    ingredients = ProductIngredientDetailSerializer(many=True, read_only=True)
    ingredientsCount = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "name", "company", "price", "unit", "piece", "productType", "viewCount", "images", "ingredientsCount", "ingredients")

    def get_ingredientsCount(self, obj: Product) -> int:
        return obj.ingredients.count()