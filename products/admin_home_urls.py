"""/admin/home 라우팅.

카테고리(대/중/소분류)·제품·배너·원료(기능성/기타) 관리 페이지와 검수용
스타일가이드 URL을 등록한다. 신규 기능 페이지는 이 urlconf 에 추가하고,
템플릿은 admin_home/base.html 을 {% extends %} 하면 디자인 시스템이 자동 적용된다.
"""

from django.urls import path

from products.admin_auth import admin_auth_required
from products.admin_home_views import (
    banner_list,
    category_big,
    category_middle,
    category_small,
    home,
    ingredient_list,
    ingredient_other,
    product_list,
    styleguide,
)

urlpatterns = [
    # /admin/home 랜딩 (로그인 후 진입 지점)
    path("", admin_auth_required(home), name="admin_home"),
    # 카테고리 · 대분류 관리 (목록/추가/수정/삭제)
    path("category/", admin_auth_required(category_big), name="admin_home_category"),
    # 카테고리 · 중분류 관리 (목록/추가/수정/삭제)
    path(
        "category/middle/",
        admin_auth_required(category_middle),
        name="admin_home_category_middle",
    ),
    # 카테고리 · 소분류 관리 (목록/추가/수정/삭제)
    path(
        "category/small/",
        admin_auth_required(category_small),
        name="admin_home_category_small",
    ),
    # 제품 관리 · 읽기 전용 목록 (추가/수정/삭제는 기존 admin 편집기로 링크)
    path("product/", admin_auth_required(product_list), name="admin_home_product"),
    # 원료 · 기능성 원료(Ingredient) 관리 (목록/추가/삭제)
    path(
        "ingredient/",
        admin_auth_required(ingredient_list),
        name="admin_home_ingredient",
    ),
    # 원료 · 기타 원료(OtherIngredient) 관리 (목록/추가/수정/삭제)
    path(
        "ingredient/other/",
        admin_auth_required(ingredient_other),
        name="admin_home_ingredient_other",
    ),
    # 배너 관리 · 목록/추가/삭제 (상세 이미지는 하위 라우트에서)
    path("banner/", admin_auth_required(banner_list), name="admin_home_banner"),
    # 검수 전용 스타일가이드 (admin 로그인 필요)
    path("_styleguide/", admin_auth_required(styleguide), name="admin_home_styleguide"),
]
