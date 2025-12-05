from django.contrib import admin

from .models import Ingredient, ProductIngredient, Product


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """성분(Ingredient) 관리용 Admin"""

    list_display = (
        "id",
        "name",
        "englishIngredient",
        "minRecommended",
        "maxRecommended",
        "effect",
        "sideEffect",
    )
    list_editable = (
        "name",
        "englishIngredient",
        "minRecommended",
        "maxRecommended",
        "effect",
        "sideEffect",
    )
    search_fields = ("name", "englishIngredient", "effect", "sideEffect")
    list_filter = ()
    ordering = ("name",)


@admin.register(ProductIngredient)
class ProductIngredientAdmin(admin.ModelAdmin):
    """제품-성분 연결 관리용 Admin"""

    list_display = ("id", "product", "ingredient", "amount")
    search_fields = (
        "product__name",
        "ingredient__name",
        "ingredient__englishIngredient",
    )
    list_filter = ("ingredient",)
    autocomplete_fields = ("product", "ingredient")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """제품 관리에서 성분 관계를 같이 볼 수 있게 설정"""

    list_display = ("id", "name", "company", "price")
    search_fields = ("name", "company")
    list_filter = ()
    ordering = ("name",)

    # 제품 상세 페이지에서 관련 성분 관계를 인라인으로 볼 수 있도록 설정할 수도 있음
    # 필요하면 아래 주석을 풀고 사용
    # class ProductIngredientInline(admin.TabularInline):
    #     model = ProductIngredient
    #     extra = 1
    #
    # inlines = [ProductIngredientInline]