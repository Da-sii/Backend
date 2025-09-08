from django.urls import path
from users.views import SignUpView, SignInView, KakaoLoginView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signIn"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('auth/kakao/token/', KakaoLoginView.as_view(), name="kakao_token"),
]
