from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.http import JsonResponse
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

def apple_app_site_association(request):
    data = {
        "applinks": {
            "apps": [],
            "details": [{
                "appID": "AGQJU3FNWG.com.podostore.dasii",
                "paths": ["/product/*"]
            }]
        }
    }
    return JsonResponse(data)

def assetlinks(request):
    data = [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.dasii",
            "sha256_cert_fingerprints": ["2F:49:BD:7A:86:47:BC:FA:F5:F4:2D:40:F4:0E:D6:9A:6D:C3:36:51:C8:0A:31:B2:5A:7E:DB:E6:A8:44:18:44."]
        }
    }]
    return JsonResponse(data, safe=False)