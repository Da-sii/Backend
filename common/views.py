from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from .models import Banner

@extend_schema(
    tags=["메인-배너"],
    summary="메인 배너 목록 조회",
    description="메인 화면에 노출되는 활성 배너 이미지 목록을 반환합니다.",
)
class BannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        banners = Banner.objects.filter(is_active=True).values('id', 'image_url', 'order')
        return Response(list(banners))