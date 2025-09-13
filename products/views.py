from rest_framework import generics, parsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from products.models import Product
from products.serializers import ProductCreateSerializer, ProductReadSerializer, ProductDetailSerializer


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