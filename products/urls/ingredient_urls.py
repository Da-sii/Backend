from django.urls import path
from products.views.ingredient import GuideListView, GuideDetailView

urlpatterns = [
    path("guides/", GuideListView.as_view(), name="ingredient_guide_list"),
    path("guides/<int:pk>/", GuideDetailView.as_view(), name="ingredient_guide_detail"),
]
