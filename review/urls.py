from django.urls import path
from . import views

urlpatterns = [
    path('product/<int:product_id>/', views.PostView.as_view(), name='post-review'),
    path('<int:review_id>/', views.ReviewUpdateView.as_view(), name='update-review'),
    path('<int:review_id>/images/', views.ReviewImageView.as_view(), name='review-images'),
]
