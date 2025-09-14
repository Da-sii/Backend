from django.urls import path

from products.views import ProductCreateView, ProductDetailView, ProductRankingView, ProductListView, ProductCategoryView, ProductSearchView, MainView

urlpatterns = [
    path("add/", ProductCreateView.as_view(), name="product_add"),
    path("<int:id>/", ProductDetailView.as_view(), name="product_detail"),
    path("ranking/", ProductRankingView.as_view(), name="product_ranking"),
    path("list/", ProductListView.as_view(), name="product_list"),
    path("category/", ProductCategoryView.as_view(), name="product_category"),
    path("search/", ProductSearchView.as_view(), name="product_search"),
    path("main/", MainView.as_view(), name="product_main")
]


