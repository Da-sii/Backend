from django.urls import path

from products.views import ProductCreateView


urlpatterns = [
    path("add/", ProductCreateView.as_view(), name="product_add"),
]


