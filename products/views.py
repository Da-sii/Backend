from rest_framework import generics, parsers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound, ValidationError
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Sum, Count, Q, Subquery
from django.db.models.functions import Coalesce
from products.models import Product, BigCategory, ProductIngredient, ProductImage
from products.serializers import ProductCreateSerializer, ProductReadSerializer, ProductDetailSerializer, ProductRankingSerializer
from products.serializers import ProductsListSerializer, CategorySerializer, ProductSearchSerializer, MainSerializer
from products.utils import record_view, upload_images_to_s3

# 제품 등록
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [AllowAny]  # 인증 없이 접근 가능
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

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
    permission_classes = [AllowAny]
    lookup_field = "id"

    @extend_schema(
        summary="제품 상세 조회",
        tags=["제품"]
    )

    def get(self, request, *args, **kwargs):

        product = self.get_object()

        record_view(product)

        # serializer에 request 컨텍스트 전달

        serializer = self.get_serializer(product, context={'request': request})

        return Response(serializer.data)

# 랭킹 카테고리 (메인의 인기 카테고리와 동일 순서)
class ProductRankingCategoryView(generics.ListAPIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="랭킹 카테고리",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        # 소분류별 지난 30일 조회수 합계 순 상위 소분류 목록
        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        from products.models import SmallCategory

        small_with_views = (
            SmallCategory.objects
            .exclude(category="전체")
            .annotate(
                totalViews=Coalesce(
                    Sum(
                        "category_products__product__daily_views__views",
                        filter=Q(category_products__product__daily_views__date__gte=start_date)
                    ),
                    0,
                )
            )
            .order_by("-totalViews", "id")
        )

        categories_payload = [
            {"smallCategory": sc.category, "bigCategory": sc.bigCategory.category}
            for sc in small_with_views
        ]

        return Response({
            "topSmallCategories": categories_payload
        })

# 랭킹
class ProductRankingView(generics.ListAPIView):
    serializer_class = ProductRankingSerializer
    permission_classes = [AllowAny]

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
            # 월간: 당일 00시 기준 고정(오늘 제외)
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=30)

        # monthly의 경우 오늘은 제외하여 00시 기준 고정되도록 함
        if period == "monthly":
            queryset = Product.objects.filter(daily_views__date__gte=start_date, daily_views__date__lt=today)
        else:
            queryset = Product.objects.filter(daily_views__date__gte=start_date)

        if category and category != "전체":
            queryset = queryset.filter(category_products__category__category=category)

        ranked = queryset.annotate(totalViews=Sum("daily_views__views")).order_by("-totalViews", "id")[:50]

        # 변동 계산 컨텍스트 준비 (daily: 어제, monthly: 이전 30일)
        if period == "daily":
            prev_start = today - timedelta(days=1)
            prev_end = today
            prev_qs = Product.objects.filter(daily_views__date__gte=prev_start, daily_views__date__lt=prev_end)
        else:  # monthly (오늘 제외한 직전 30일 비교)
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

        # 인스턴스 변수에 저장하여 list 메서드에서 사용
        self.ranking_context = {"period": period, "current_ranks": current_ranks, "prev_ranks": prev_ranks}

        return ranked

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={
                'request': request,
                **(getattr(self, 'ranking_context', {}))
            })
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={
            'request': request,
            **(getattr(self, 'ranking_context', {}))
        })
        return Response(serializer.data)

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
    permission_classes = [AllowAny]

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
                description="대분류 카테고리 이름(예: 다이어트 약, 다이어트 보조제, 다이어트 식품 등). 미제공시 모든 제품 조회",
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
        bigCategory = self.request.query_params.get("bigCategory")
        smallCategory = self.request.query_params.get("smallCategory")
        sort = self.request.query_params.get("sort", "monthly_rank")

        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        qs = Product.objects.all()
        
        # bigCategory가 제공된 경우에만 필터링
        if bigCategory:
            qs = qs.filter(category_products__category__bigCategory__category=bigCategory).distinct()

        if smallCategory and smallCategory != "전체":
            qs = qs.filter(category_products__category__category=smallCategory).distinct()

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
        # 월간 랭킹 기준: 오늘 제외하여 00시 기준 고정
        return (
            qs.annotate(
                totalViews=Coalesce(
                    Sum(
                        "daily_views__views",
                        filter=Q(daily_views__date__gte=start_date) & Q(daily_views__date__lt=today),
                    ),
                    0,
                )
            )
            .order_by("-totalViews", "id")
        )

# 제품 카테고리 조회
class ProductCategoryView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="카테고리 조회",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return BigCategory.objects.prefetch_related("smallCategories").order_by("id")

# 검색
class ProductSearchView(generics.ListAPIView):
    serializer_class = ProductSearchSerializer
    permission_classes = [AllowAny]

    class ListPagination(PageNumberPagination):
        page_size = 10
        page_query_param = "page"
        page_size_query_param = None
        max_page_size = 10

    pagination_class = ListPagination

    @extend_schema(
        summary="제품 검색",
        parameters=[
            OpenApiParameter(
                name="word",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="검색어(제품명, 회사명, 기능성 원료명)",
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
        sort = self.request.query_params.get("sort", "monthly_rank")
        query = self.request.query_params.get("word")

        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        qs = Product.objects.all()

        if query:
            ingredient_product_ids = ProductIngredient.objects.filter(
                Q(ingredient__name__icontains=query)
            ).values("product_id")

            qs = qs.filter(
                Q(name__icontains=query) |
                Q(company__icontains=query) |
                Q(id__in=Subquery(ingredient_product_ids))
            ).distinct()

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
                    Sum(
                        "daily_views__views",
                        filter=Q(daily_views__date__gte=start_date) & Q(daily_views__date__lt=today),
                    ),
                    0,
                )
            )
            .order_by("-totalViews", "id")
        )

# 메인
class MainView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="메인 화면",
        tags=["제품"]
    )
    def get(self, request, *args, **kwargs):
        # 소분류별 지난 30일 조회수 합계 순 상위 소분류 목록
        today = timezone.now().date()
        start_date = today - timedelta(days=30)

        from products.models import SmallCategory

        small_with_views = (
            SmallCategory.objects
            .exclude(category="전체")
            .annotate(
                totalViews=Coalesce(
                    Sum(
                        "category_products__product__daily_views__views",
                        filter=Q(category_products__product__daily_views__date__gte=start_date)
                    ),
                    0,
                )
            )
            .order_by("-totalViews", "id")
        )

        # 오늘 조회수 상위 10개 제품
        top_today_products = (
            Product.objects.annotate(
                todayViews=Coalesce(
                    Sum("daily_views__views", filter=Q(daily_views__date=today)),
                    0,
                )
            )
            .order_by("-todayViews", "id")[:10]
        )

        categories_payload = [
            {"smallCategory": sc.category, "bigCategory": sc.bigCategory.category}
            for sc in small_with_views
        ]

        serializer = MainSerializer(top_today_products, many=True)

        return Response({
            "topSmallCategories": categories_payload,
            "topProductsToday": serializer.data,
        })

# 제품 이미지 등록
class UploadProductImageView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @extend_schema(
        summary="제품 이미지 등록",
        tags=["제품"]
    )
    def post(self, request, id):
        try:
            product = Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise NotFound("제품을 찾을 수 없습니다.")
        
        # 여러 이미지 파일 받기
        images = request.FILES.getlist('images')
        
        if not images:
            raise ValidationError("이미지 파일이 필요합니다.")
        
        # S3 업로드 및 ProductImage 저장
        uploaded_images = upload_images_to_s3(product, images)
        ProductImage.objects.bulk_create(uploaded_images)
        
        return Response({"success": True, "message": f"{len(uploaded_images)}개의 이미지가 등록되었습니다."}, status=201)
