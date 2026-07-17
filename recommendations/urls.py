from django.urls import path
from recommendations.views.recommendation import RecommendationView

urlpatterns = [
    path("", RecommendationView.as_view(), name="recommendations"),
]