from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.models import Product
from products.serializers import ProductCreateSerializer, ProductReadSerializer


# 제품 등록
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated] # 접근 권한 확인

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        product = create_serializer.save()

        read_serializer = ProductReadSerializer(product)
        return Response({"success": True, "product": read_serializer.data}, status=201)

