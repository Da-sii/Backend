from django.urls import path

from products.views import ProductDetailView, ProductRankingView, ProductRankingCategoryView, ProductListView, \
    ProductCategoryView, ProductSearchView, MainView, UploadProductImageView, ProductRequestView

urlpatterns = [
    path("ranking/", ProductRankingView.as_view(), name="product_ranking"),
    path("ranking/category/", ProductRankingCategoryView.as_view(), name="product_ranking_category"),
    path("list/", ProductListView.as_view(), name="product_list"),
    path("category/", ProductCategoryView.as_view(), name="product_category"),
    path("search/", ProductSearchView.as_view(), name="product_search"),
    path("main/", MainView.as_view(), name="product_main"),
    path("<int:id>/images/", UploadProductImageView.as_view(), name="product_image_add"),
    path("<int:id>/", ProductDetailView.as_view(), name="product_detail"),
    path("request/", ProductRequestView.as_view(), name="product_request"),
]