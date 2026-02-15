from rest_framework import generics
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from products.models import BigCategory
from products.serializers import BigCategorySerializer


# 제품 카테고리 조회
class ProductCategoryView(generics.ListAPIView):
    serializer_class = BigCategorySerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="카테고리 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return (
            BigCategory.objects
            .prefetch_related(
                "middle_categories__small_categories"
            )
            .order_by("id")
        )