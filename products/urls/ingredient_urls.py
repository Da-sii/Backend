from django.urls import path
from products.views.ingredient import GuideListView

urlpatterns = [
    path("guides/", GuideListView.as_view(), name="ingredient_guide_list"),
]
