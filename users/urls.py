from django.urls import path
from users.views import SignUpView, SignInView, KakaoLoginView, LogoutView, NicknameUpdateView, PasswordChangeView, PasswordResetView, PhoneNumberFindAccountView, MyPageUserInfoView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signIn"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("kakao/token/", KakaoLoginView.as_view(), name="kakao_token"),
    path("nickname/", NicknameUpdateView.as_view(), name="nickname_update"),
    path("password/", PasswordChangeView.as_view(), name="password_change"),
    path("password/reset/", PasswordResetView.as_view(), name="password_reset"),
    path("phone/account-info/", PhoneNumberFindAccountView.as_view(), name="find_account"),
    path("mypage/", MyPageUserInfoView.as_view(), name="mypage_user_info"),
]
