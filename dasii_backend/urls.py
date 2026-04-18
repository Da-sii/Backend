from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from . import views

urlpatterns = [
    path("", views.support_root, name="support_root"),  # 루트 경로 - 고객지원 정보 페이지
    
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    path("admin/", include("products.admin_urls")),  # 관리자 페이지 (인증 필요) - 먼저 매칭
    path("django-admin/", admin.site.urls),  # Django 기본 admin (다른 경로로 이동)

    path("auth/", include("auth.urls")), # auth 앱 라우팅
    path("auth/", include("users.urls")), # users 앱 라우팅
    path("auth/", include("socials.urls")), # socials 앱 라우팅
    path("products/", include("products.urls.product_urls")), # products 앱 라우팅
    path("ingredients/", include("products.urls.ingredient_urls")),
    path("review/", include("review.urls")), # review 앱 라우팅
    path("banners/", include("common.urls") ),
]
