from django.urls import path

from products.views import ProductCreateView, ProductDetailView, ProductRankingView, ProductListView, ProductCategoryView, ProductSearchView, MainView, UploadProductImageView, big_category_form, small_category_form, product_form, product_edit, ingredient_form

urlpatterns = [
    path("add/", ProductCreateView.as_view(), name="product_add"),
    path("ranking/", ProductRankingView.as_view(), name="product_ranking"),
    path("list/", ProductListView.as_view(), name="product_list"),
    path("category/", ProductCategoryView.as_view(), name="product_category"),
    path("search/", ProductSearchView.as_view(), name="product_search"),
    path("main/", MainView.as_view(), name="product_main"),
    path("<int:id>/images/", UploadProductImageView.as_view(), name="product_image_add"),
    path("<int:id>/", ProductDetailView.as_view(), name="product_detail"),
    path("big-category/", big_category_form, name="big_category_form"),
    path("small-category/", small_category_form, name="small_category_form"),
    path("product/", product_form, name="product_form"),
    path("product/<int:product_id>/edit/", product_edit, name="product_edit"),
    path("ingredient/", ingredient_form, name="ingredient_form"),
]