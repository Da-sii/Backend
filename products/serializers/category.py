from rest_framework import serializers

from products.models import BigCategory, MiddleCategory


class BigCategorySerializer(serializers.ModelSerializer):
    middleCategories = serializers.SerializerMethodField()

    class Meta:
        model = BigCategory
        fields = ("category", "middleCategories")

    def get_middleCategories(self, obj):
        middle_qs = obj.middle_categories.order_by("id")
        return MiddleCategorySerializer(middle_qs, many=True).data

class MiddleCategorySerializer(serializers.ModelSerializer):
    smallCategories = serializers.SerializerMethodField()

    class Meta:
        model = MiddleCategory
        fields = ("category", "smallCategories")

    def get_smallCategories(self, obj):
        return list(
            obj.small_categories
               .order_by("id")
               .values_list("category", flat=True)
        )