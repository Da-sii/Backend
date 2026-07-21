from django.urls import path
from recommendations.views import RecommendationView, SavedRecommendationView

urlpatterns = [
    path("", RecommendationView.as_view(), name="recommendations"),
    path("saved/", SavedRecommendationView.as_view(), name="recommendation-saved"),
]