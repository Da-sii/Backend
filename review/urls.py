from django.urls import path
from . import views

urlpatterns = [
    path('myReviews/<int:review_id>/', views.UserReviewsView.as_view(), name='user-reviews'),
    path('product/<int:product_id>/', views.PostView.as_view(), name='post-review'),
    path('product/<int:product_id>/reviews/<int:review_id>/', views.ReviewListView.as_view(), name='get-reviews'),
    path('product/<int:product_id>/check/', views.UserReviewCheckView.as_view(), name='check-user-review'),
    path('product/<int:product_id>/images/<int:image_id>/', views.ProductReviewImagesView.as_view(), name='product-review-images'),
    path('product/<int:product_id>/rating/', views.ProductRatingStatsView.as_view(), name='product-rating-stats'),
    path('image/<int:image_id>/', views.ReviewImageDetailView.as_view(), name='review-image-detail'),
    path('detail/<int:review_id>/', views.ReviewDetailView.as_view(), name='review-detail'),
    path('<int:review_id>/', views.ReviewUpdateView.as_view(), name='update-review'),
    path('<int:review_id>/delete/', views.ReviewDeleteView.as_view(), name='delete-review'),
    path('<int:review_id>/images/', views.ReviewImageView.as_view(), name='review-images'),
    path('<int:review_id>/images/<int:image_id>/', views.ReviewImageDeleteView.as_view(), name='delete-review-image'),
    path('<int:review_id>/report/', views.ReviewReportView.as_view(), name='report-review'),
    path('<int:review_id>/block/', views.BlockUserReviewsView.as_view(), name='block-user-reviews'),
    path('random-products/', views.RandomProductsView.as_view(), name='random-products'),
]
