from django.urls import path
from users.views import SignUpView, SignInView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signIn"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]