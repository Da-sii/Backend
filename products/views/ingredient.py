from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from products.models import IngredientGuide
from products.serializers.ingredient import GuideListSerializer, GuideDetailSerializer


# 성분 가이드 리스트(검색)
class GuideListView(generics.ListAPIView):
    serializer_class = GuideListSerializer
    permission_classes = [AllowAny]

    class ListPagination(PageNumberPagination):
        page_size = 10
        page_query_param = 'page'
        page_size_query_param = None
        max_page_size = 10

    pagination_class = ListPagination

    @extend_schema(
        summary="성분 가이드 리스트 (검색 + 페이지네이션)",
        description="""
        - search: 성분명 검색 (공백 무시 부분 검색 가능)
        - page: 페이지 번호
        - 정렬은 기본 가나다순(오름차순) 고정
        """,
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="성분명 검색 (띄어쓰기 무시 부분검색 지원)"
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="페이지 번호 (기본 10개씩 반환)"
            ),
        ],
        tags=["성분 가이드"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        keyword = self.request.query_params.get("search", "").strip()

        queryset = (
            IngredientGuide.objects
            .select_related("ingredient")
            .order_by("ingredient__name") # 항상 가나다 순
        )

        if keyword:
            keyword_no_space = keyword.replace(" ", "")

            queryset = queryset.filter(
                Q(ingredient__name__icontains=keyword) |
                Q(ingredient__name__icontains=keyword_no_space)
            )

        return queryset

# 성분 가이드 상세
class GuideDetailView(generics.RetrieveAPIView):
    queryset = IngredientGuide.objects.select_related("ingredient")
    serializer_class = GuideDetailSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="성분 가이드 상세",
        tags=["성분 가이드"]
    )
    def get(self, request, *args, **kwargs):
        ingredient_guide = self.get_object()

        serializer = self.get_serializer(ingredient_guide, context={'request': request})

        return Response(serializer.data)