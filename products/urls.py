from django.urls import path

from products.views import ProductCreateView, ProductDetailView, ProductRankingView

urlpatterns = [
    path("add/", ProductCreateView.as_view(), name="product_add"),
    path("<int:id>/", ProductDetailView.as_view(), name="product_detail"),
    path("ranking/", ProductRankingView.as_view(), name="product_ranking"),
]


