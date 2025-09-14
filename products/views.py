from rest_framework import generics, parsers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from products.models import Product
from products.serializers import ProductCreateSerializer, ProductReadSerializer, ProductDetailSerializer, ProductRankingSerializer
from products.serializers import ProductsListSerializer
from products.utils import record_view


# 제품 등록
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated] # 접근 권한 확인
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        product = create_serializer.save()

        read_serializer = ProductReadSerializer(product)
        
        return Response({"success": True, "product": read_serializer.data}, status=201)

    @extend_schema(
        summary="제품 등록",
        tags=["제품"]
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

# 제품 상세 (GET /products/<id>/)
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticated] # 접근 권한 확인
    lookup_field = "id"

    @extend_schema(
        summary="제품 상세 조회",
        tags=["제품"]
    )

    def get(self, request, *args, **kwargs):
        product = self.get_object()
        record_view(product)

        return self.retrieve(request, *args, **kwargs)

# 랭킹
class ProductRankingView(generics.ListAPIView):
    serializer_class = ProductRankingSerializer
    permission_classes = [IsAuthenticated] # 접근 권한 확인
    class RankingPagination(PageNumberPagination):
        page_size = 10                # 고정 10개
        page_query_param = "page"     # 페이지 번호만 허용
        page_size_query_param = None   # 클라이언트가 변경 불가
        max_page_size = 10

    pagination_class = RankingPagination

    def get_queryset(self):
        period = self.request.query_params.get("period", "daily")
        category = self.request.query_params.get("category")
        today = timezone.now().date()

        if period == "daily":
            start_date = today - timedelta(days=1)
        elif period == "monthly":
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=30)

        queryset = Product.objects.filter(daily_views__date__gte=start_date)

        if category and category != "전체":
            queryset = queryset.filter(category_products__category__category=category)

        ranked = queryset.annotate(totalViews=Sum("daily_views__views")).order_by("-totalViews", "id")[:50]

        # 변동 계산 컨텍스트 준비 (daily: 어제, monthly: 이전 30일)
        if period == "daily":
            prev_start = today - timedelta(days=1)
            prev_end = today
            prev_qs = Product.objects.filter(daily_views__date__gte=prev_start, daily_views__date__lt=prev_end)
        else:  # monthly
            prev_start = today - timedelta(days=60)
            prev_end = today - timedelta(days=30)
            prev_qs = Product.objects.filter(daily_views__date__gte=prev_start, daily_views__date__lt=prev_end)

        if category and category != "전체":
            prev_qs = prev_qs.filter(category_products__category__category=category)

        prev_ranked = list(
            prev_qs.annotate(totalViews=Sum("daily_views__views")).order_by("-totalViews", "id")[:50].values_list("id", flat=True)
        )
        prev_ranks = {pid: idx + 1 for idx, pid in enumerate(prev_ranked)}

        current_ranks = {product.id: idx + 1 for idx, product in enumerate(ranked)}
        self.serializer_class.context = {"period": period, "current_ranks": current_ranks, "prev_ranks": prev_ranks}

        return ranked

    @extend_schema(
        summary="랭킹 조회",
        parameters=[
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="랭킹 기간 (기본: daily)",
                required=False,
                enum=["daily", "monthly"],
            ),
            OpenApiParameter(
                name="category",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="카테고리 이름 (예: 전체, 체지방 관리 등). 기본: 전체",
                required=False,
            ),
        ],
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

# 제품 리스트 (필터/정렬/페이징)
class ProductListView(generics.ListAPIView):
    serializer_class = ProductsListSerializer
    permission_classes = [IsAuthenticated]

    class ListPagination(PageNumberPagination):
        page_size = 10
        page_query_param = "page"
        page_size_query_param = None
        max_page_size = 10

    pagination_class = ListPagination

    @extend_schema(
        summary="제품 리스트 조회",
        parameters=[
            OpenApiParameter(
                name="bigCategory",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="대분류 카테고리 이름(예: 다이어트 약, 다이어트 식품 등). 기본: 다이어트 약",
                required=False,
            ),
            OpenApiParameter(
                name="smallCategory",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="소분류 카테고리 이름(예: 전체, 체지방 관리 등). 기본: 전체",
                required=False,
            ),
            OpenApiParameter(
                name="sort",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="정렬: monthly_rank | price_asc | price_desc | review_desc (기본: monthly_rank)",
                required=False,
                enum=["monthly_rank", "price_asc", "price_desc", "review_desc"],
            ),
        ],
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        bigCategory = self.request.query_params.get("bigCategory", "다이어트 약")
        smallCategory = self.request.query_params.get("smallCategory")
        sort = self.request.query_params.get("sort", "monthly_rank")
        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        qs = Product.objects.all()
        if bigCategory:
            qs = qs.filter(category_products__category__bigCategory__category=bigCategory)

        if smallCategory and smallCategory != "전체":
            qs = qs.filter(category_products__category__category=smallCategory)

        if sort == "price_asc":
            return qs.order_by("price", "id")
        if sort == "price_desc":
            return qs.order_by("-price", "id")
        if sort == "review_desc":
            return (
                qs.annotate(review_count=Count("reviews", distinct=True))
                .order_by("-review_count", "id")
            )

        # default: monthly_rank (최근 30일 조회수 합계 기준)
        # 조회수 없는 상품도 포함(0으로 취급)하여 정렬
        return (
            qs.annotate(
                totalViews=Coalesce(
                    Sum("daily_views__views", filter=Q(daily_views__date__gte=start_date)),
                    0,
                )
            )
            .order_by("-totalViews", "id")
        )