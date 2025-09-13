from rest_framework import generics, parsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from django.db.models import Sum
from products.models import Product
from products.serializers import ProductCreateSerializer, ProductReadSerializer, ProductDetailSerializer, ProductRankingSerializer
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

# 제품 상세 (GET /products/<id>/)
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAuthenticated] # 접근 권한 확인
    lookup_field = "id"

    def get(self, request, *args, **kwargs):
        product = self.get_object()
        record_view(product)
        return self.retrieve(request, *args, **kwargs)

# 랭킹
class ProductRankingView(generics.ListAPIView):
    serializer_class = ProductRankingSerializer
    permission_classes = [IsAuthenticated] # 접근 권한 확인
    pagination_class = None

    def get_queryset(self):
        period = self.request.query_params.get("period", "daily")
        today = timezone.now().date()

        if period == "daily":
            start_date = today - timedelta(days=1)
        elif period == "monthly":
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=30)

        return (
            Product.objects.filter(daily_views__date__gte=start_date)
            .annotate(totalViews=Sum("daily_views__views"))
            .order_by("-totalViews")[:50]
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="랭킹 기간 (기본: daily)",
                required=False,
                enum=["daily", "monthly"],
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)