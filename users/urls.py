# users/urls.py
from django.urls import path
from .views import kakao_token_view

urlpatterns = [
    path('auth/kakao/token/', kakao_token_view),
]
