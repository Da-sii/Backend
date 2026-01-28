import json
from typing import List, Dict, Any
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg
from django.db import transaction
from rest_framework import serializers

from products.models import Product, ProductImage, Ingredient, ProductIngredient, BigCategory, OtherIngredient, \
    ProductOtherIngredient, ProductRequest
from products.utils import upload_images_to_s3

class ProductIngredientInputSerializer(serializers.Serializer):
    ingredientId = serializers.IntegerField()
    amount = serializers.CharField()

class ProductCreateSerializer(serializers.ModelSerializer):
    # 여러 이미지 파일
    images = serializers.ListField(
        child=serializers.ImageField(), required=False, allow_empty=True
    )
    # 문자열(JSON) 또는 배열로 받음
    ingredients = serializers.JSONField(required=False)

    class Meta:
        model = Product
        fields = ("name", "company", "productType", "images", "ingredients")

    def validate_ingredients(self, value) -> List[Dict[str, Any]]:
        if not value:
            return []

        # 이미 리스트인 경우 (JSON 요청)
        if isinstance(value, list):
            return value
        
        # 문자열인 경우 (form-data 요청)
        if isinstance(value, str):
            try:
                data = json.loads(value)  # 문자열 → JSON 변환
            except json.JSONDecodeError:
                raise serializers.ValidationError("ingredients는 JSON 형식이어야 합니다.")

            if not isinstance(data, list):
                raise serializers.ValidationError("ingredients는 배열이어야 합니다.")

            return data
        
        raise serializers.ValidationError("ingredients는 배열 또는 JSON 문자열이어야 합니다.")


    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Product:
        images: List[str] = validated_data.pop("images", [])
        ingredients_input: List[Dict[str, Any]] = validated_data.pop("ingredients", [])
        product = Product.objects.create(**validated_data)

        # --- S3 업로드 ---
        if images:
            uploaded_images = upload_images_to_s3(product, images)
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
        fields = ("id", "name", "company", "productType", "images", "ingredients")

class ProductIngredientDetailSerializer(serializers.ModelSerializer):
    ingredientName = serializers.CharField(source="ingredient.name")
    mainIngredient = serializers.CharField(source="ingredient.mainIngredient")
    minRecommended = serializers.CharField(source="ingredient.minRecommended")
    maxRecommended = serializers.CharField(source="ingredient.maxRecommended")
    effect = serializers.JSONField(source="ingredient.effect")
    sideEffect = serializers.JSONField(source="ingredient.sideEffect")
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProductIngredient
        fields = ("ingredientName", "mainIngredient", "amount", "minRecommended", "maxRecommended", "effect", "sideEffect", "status")

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

class OtherIngredientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherIngredient
        fields = ("id", "name")

class ProductOtherIngredientSerializer(serializers.ModelSerializer):
    otherIngredientName = serializers.CharField(source="other_ingredient.name")

    class Meta:
        model = ProductOtherIngredient
        fields = ("otherIngredientName",)

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    reviewImages = serializers.SerializerMethodField()
    ingredients = ProductIngredientDetailSerializer(many=True, read_only=True)
    ingredientsCount = serializers.SerializerMethodField()
    otherIngredients = ProductOtherIngredientSerializer(many=True, read_only=True, source="product_other_ingredients")
    otherIngredientsCount = serializers.SerializerMethodField()
    ranking = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    reviewAvg = serializers.SerializerMethodField()
    isMyReview = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "name", "company", "productType", "coupang", "isMyReview", "reviewCount", "reviewAvg", "ranking", "images", "reviewImages", "ingredientsCount", "ingredients", "otherIngredientsCount", "otherIngredients")

    def get_reviewImages(self, obj):
        # 해당 제품의 리뷰 이미지를 최신순 6개 반환
        from review.models import ReviewImage
        review_images = ReviewImage.objects.filter(
            review__product=obj
        ).order_by('-id')[:6]
        return [{'url': img.url} for img in review_images]

    def get_reviewCount(self, obj):
        return obj.reviews.count()

    def get_reviewAvg(self, obj):
        agg = obj.reviews.aggregate(avg=Avg("rate"))
        value = agg.get("avg")
        return round(float(value), 2) if value is not None else None

    def get_ingredientsCount(self, obj: Product) -> int:
        return obj.ingredients.count()

    def get_otherIngredientsCount(self, obj: Product) -> int:
        return obj.product_other_ingredients.count()

    def get_ranking(self, obj):
        # 카테고리별 월간 랭킹
        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        # 이 제품이 속한 모든 소분류 카테고리 수집
        category_pairs = list(
            obj.category_products.select_related("category__bigCategory").values_list(
                "category_id",
                "category__bigCategory__category",
                "category__category",
            )
        )

        results = []
        for category_id, big_name, small_name in category_pairs:
            ranked_ids = list(
                Product.objects.filter(
                    category_products__category_id=category_id,
                    daily_views__date__gte=start_date,
                    daily_views__date__lt=today,  # 오늘 제외하여 00시 기준 고정
                )
                .annotate(totalViews=Sum("daily_views__views"))
                .order_by("-totalViews", "id")
                .values_list("id", flat=True)[:50]
            )

            try:
                rank = ranked_ids.index(obj.id) + 1
            except ValueError:
                rank = None  # 50위 밖

            results.append({"bigCategory": big_name, "smallCategory": small_name, "monthlyRank": rank})

        return results

    def get_isMyReview(self, obj):
        # 로그인한 사용자가 해당 제품에 리뷰를 작성했는지 확인
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.reviews.filter(user=request.user).exists()
        return False

class ProductRankingSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    rankDiff = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    reviewAvg = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "name", "image", "company", "reviewCount", "reviewAvg", "rankDiff")

    def get_image(self, obj):
        first_image = obj.images.order_by("id").first()
        return first_image.url if first_image else None

    def get_rankDiff(self, obj):
        current_ranks = self.context.get("current_ranks", {})
        prev_ranks = self.context.get("prev_ranks", {})
        current = current_ranks.get(obj.id)
        prev = prev_ranks.get(obj.id)

        if current is None or prev is None:
            return None  # 이전 50위권 밖이거나 데이터 없음 → NEW 처리 가능

        return prev - current  # 양수면 상승, 음수면 하락, 0이면 동일

    def get_reviewCount(self, obj):
        return obj.reviews.count()

    def get_reviewAvg(self, obj):
        agg = obj.reviews.aggregate(avg=Avg("rate"))
        value = agg.get("avg")
        return round(float(value), 2) if value is not None else None

class ProductsListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    reviewAvg = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ("id", "name", "image", "company", "reviewCount", "reviewAvg")

    def get_image(self, obj):
        first_image = obj.images.order_by("id").first()
        return first_image.url if first_image else None

    def get_reviewCount(self, obj):
        return obj.reviews.count()

    def get_reviewAvg(self, obj):
        agg = obj.reviews.aggregate(avg=Avg("rate"))
        value = agg.get("avg")
        return round(float(value), 2) if value is not None else None

class CategorySerializer(serializers.ModelSerializer):
    smallCategories = serializers.SerializerMethodField()

    class Meta:
        model = BigCategory
        fields = ("category", "smallCategories")

    def get_smallCategories(self, obj):
        return list(obj.smallCategories.order_by("id").values_list("category", flat=True))

class ProductSearchSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    reviewAvg = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "name", "image", "company", "reviewCount", "reviewAvg")

    def get_image(self, obj):
        first_image = obj.images.order_by("id").first()
        return first_image.url if first_image else None

    def get_reviewCount(self, obj):
        return obj.reviews.count()

    def get_reviewAvg(self, obj):
        agg = obj.reviews.aggregate(avg=Avg("rate"))
        value = agg.get("avg")
        return round(float(value), 2) if value is not None else None

class MainSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    reviewCount = serializers.SerializerMethodField()
    reviewAvg = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "name", "image", "company", "reviewCount", "reviewAvg")

    def get_image(self, obj):
        first_image = obj.images.order_by("id").first()
        return first_image.url if first_image else None

    def get_reviewCount(self, obj):
        return obj.reviews.count()

    def get_reviewAvg(self, obj):
        agg = obj.reviews.aggregate(avg=Avg("rate"))
        value = agg.get("avg")
        return round(float(value), 2) if value is not None else None

class ProductRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRequest
        fields = ("content", )

    class ProductRequestSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProductRequest
            fields = ("content",)