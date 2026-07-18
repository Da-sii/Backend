from django.urls import path
from recommendations.views import RecommendationView

urlpatterns = [
    path("", RecommendationView.as_view(), name="recommendations"),
]