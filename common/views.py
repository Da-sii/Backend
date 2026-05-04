from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.http import JsonResponse
from django.shortcuts import redirect
from .models import Banner

@extend_schema(
    tags=["메인-배너"],
    summary="메인 배너 목록 조회",
    description="메인 화면에 노출되는 활성 배너 이미지 목록을 반환합니다.",
)
class BannerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        banners = Banner.objects.filter(is_active=True).values(
            'id', 'image_url', 'detail_image_url', 'order'
        )
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

def product_fallback(request, product_id):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'iphone' in user_agent or 'ipad' in user_agent:
        return redirect('https://apps.apple.com/kr/app/%EB%8B%A4%EC%8B%9C-%EB%8B%A4%EC%9D%B4%EC%96%B4%ED%8A%B8-%EB%B3%B4%EC%A1%B0%EC%A0%9C-%EC%84%B1%EB%B6%84-%EB%B6%84%EC%84%9D-%EB%B0%8F-%ED%9B%84%EA%B8%B0-%EC%84%9C%EB%B9%84%EC%8A%A4/id6754357876')
    else:
        return redirect('https://play.google.com/store/apps/details?id=com.dasii')