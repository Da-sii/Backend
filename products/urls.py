from django.urls import path

from products.views import ProductCreateView


urlpatterns = [
    path("products/", ProductCreateView.as_view(), name="product_create"),
]


