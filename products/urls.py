from django.urls import path

from products.views import ProductCreateView, ProductDetailView


urlpatterns = [
    path("add/", ProductCreateView.as_view(), name="product_add"),
    path("<int:id>/", ProductDetailView.as_view(), name="product_detail"),
]


