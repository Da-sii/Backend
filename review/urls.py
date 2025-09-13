from django.urls import path
from . import views

urlpatterns = [
    path('product/<int:product_id>/', views.PostView.as_view(), name='post-review'),
    path('product/<int:product_id>/reviews/', views.ReviewListView.as_view(), name='get-reviews'),
    path('product/<int:product_id>/images/', views.ProductReviewImagesView.as_view(), name='product-review-images'),
    path('product/<int:product_id>/rating/', views.ProductRatingStatsView.as_view(), name='product-rating-stats'),
    path('<int:review_id>/', views.ReviewUpdateView.as_view(), name='update-review'),
    path('<int:review_id>/images/', views.ReviewImageView.as_view(), name='review-images'),
    path('<int:review_id>/images/<int:image_id>/', views.ReviewImageDeleteView.as_view(), name='delete-review-image'),
]
