from django.urls import path
from products.admin_views import (
    big_category_form, big_category_edit, small_category_form, small_category_edit,
    product_form, product_edit, ingredient_form, ingredient_edit,
    big_category_delete, small_category_delete, ingredient_delete
)
from products.admin_auth import admin_auth_required, admin_logout, admin_login_view

def admin_main(request):
    """관리자 메인 페이지"""
    from django.shortcuts import render
    return render(request, 'products/admin_main.html')

urlpatterns = [
    path("login/", admin_login_view, name="admin_login"),  # 로그인: ADMIN_CODE 입력
    path("", admin_auth_required(admin_main), name="admin_main"),  # 메인 페이지 (로그인 필요)
    path("big-category/", admin_auth_required(big_category_form), name="admin_big_category_form"),
    path("big-category/<int:category_id>/", admin_auth_required(big_category_edit), name="admin_big_category_edit"),
    path("big-category/<int:category_id>/delete/", admin_auth_required(big_category_delete), name="admin_big_category_delete"),
    path("small-category/", admin_auth_required(small_category_form), name="admin_small_category_form"),
    path("small-category/<int:category_id>/", admin_auth_required(small_category_edit), name="admin_small_category_edit"),
    path("small-category/<int:category_id>/delete/", admin_auth_required(small_category_delete), name="admin_small_category_delete"),
    path("product/", admin_auth_required(product_form), name="admin_product_form"),
    path("product/<int:product_id>/", admin_auth_required(product_edit), name="admin_product_edit"),
    path("ingredient/", admin_auth_required(ingredient_form), name="admin_ingredient_form"),
    path("ingredient/<int:ingredient_id>/", admin_auth_required(ingredient_edit), name="admin_ingredient_edit"),
    path("ingredient/<int:ingredient_id>/delete/", admin_auth_required(ingredient_delete), name="admin_ingredient_delete"),
    path("logout/", admin_logout, name="admin_logout"),
]

