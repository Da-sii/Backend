from django.urls import path, include
from products.admin_views import (
    big_category_form, big_category_edit, big_category_delete,
    middle_category_form, middle_category_edit, middle_category_delete,
    small_category_form, small_category_edit, small_category_delete,
    product_form, product_edit, product_delete,
    ingredient_form, ingredient_edit, ingredient_delete,
    other_ingredient_form, other_ingredient_edit, other_ingredient_delete,
    product_request_list, admin_product_request_delete,
    ingredient_guide_form, ingredient_guide_edit, ingredient_guide_delete, import_csv_view
)
from products.admin_auth import admin_auth_required, admin_logout, admin_login_view


def admin_main(request):
    from django.shortcuts import render
    return render(request, 'products/admin_main.html')


urlpatterns = [
    # ================= 로그인 =================
    path("login/", admin_login_view, name="admin_login"),
    path("logout/", admin_logout, name="admin_logout"),

    # ================= 메인 =================
    path("", admin_auth_required(admin_main), name="admin_main"),

    # ================= 대분류 =================
    path("big-category/", admin_auth_required(big_category_form), name="admin_big_category_form"),
    path("big-category/<int:category_id>/", admin_auth_required(big_category_edit), name="admin_big_category_edit"),
    path("big-category/<int:category_id>/delete/", admin_auth_required(big_category_delete), name="admin_big_category_delete"),

    # ================= 중분류 =================
    path("middle-category/", admin_auth_required(middle_category_form), name="admin_middle_category_form"),
    path("middle-category/<int:category_id>/", admin_auth_required(middle_category_edit), name="admin_middle_category_edit"),
    path("middle-category/<int:category_id>/delete/", admin_auth_required(middle_category_delete), name="admin_middle_category_delete"),

    # ================= 소분류 =================
    path("small-category/", admin_auth_required(small_category_form), name="admin_small_category_form"),
    path("small-category/<int:category_id>/", admin_auth_required(small_category_edit), name="admin_small_category_edit"),
    path("small-category/<int:category_id>/delete/", admin_auth_required(small_category_delete), name="admin_small_category_delete"),

    # ================= 제품 =================
    path("product/", admin_auth_required(product_form), name="admin_product_form"),
    path("product/<int:product_id>/edit/", admin_auth_required(product_edit), name="admin_product_edit"),
    path("product/<int:product_id>/delete/", admin_auth_required(product_delete), name="admin_product_delete"),

    # ================= 성분 =================
    path("ingredient/", admin_auth_required(ingredient_form), name="admin_ingredient_form"),
    path("ingredient/<int:ingredient_id>/", admin_auth_required(ingredient_edit), name="admin_ingredient_edit"),
    path("ingredient/<int:ingredient_id>/delete/", admin_auth_required(ingredient_delete), name="admin_ingredient_delete"),

    # ================= 성분 가이드 =================
    path("ingredient-guide/", admin_auth_required(ingredient_guide_form), name="admin_ingredient_guide_form"),
    path("ingredient-guide/<int:pk>/edit/", admin_auth_required(ingredient_guide_edit), name="admin_ingredient_guide_edit"),
    path("ingredient-guide/<int:pk>/delete/", admin_auth_required(ingredient_guide_delete), name="admin_ingredient_guide_delete"),

    # ================= 기타 성분 =================
    path("other-ingredient/", admin_auth_required(other_ingredient_form), name="admin_other_ingredient_form"),
    path("other-ingredient/<int:pk>/edit/", admin_auth_required(other_ingredient_edit), name="admin_other_ingredient_edit"),
    path("other-ingredient/<int:pk>/delete/", admin_auth_required(other_ingredient_delete), name="admin_other_ingredient_delete"),

    # ================= 제품 요청 =================
    path("product-requests/", admin_auth_required(product_request_list), name="admin_product_request_list"),
    path("product-requests/<int:request_id>/delete/", admin_auth_required(admin_product_request_delete), name="admin_product_request_delete"),

    # ================== 데이터 수집 ===============
    path("import-csv/", admin_auth_required(import_csv_view), name="admin_import_csv"),

    # ================= 배너 관리 =================
    path("banners/", include("common.admin.admin_urls")),
]