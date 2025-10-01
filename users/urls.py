from django.urls import path
from users.views import SignUpView, SignInView, KakaoLoginView, LogoutView, KakaoLogoutView, NicknameUpdateView, PasswordChangeView, PasswordResetView, EmailCheckView, EmailPasswordResetView, PhoneNumberFindAccountView, PhoneNumberAccountInfoView, MyPageUserInfoView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signIn"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("kakao/logout/", KakaoLogoutView.as_view(), name="kakao_logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("kakao/token/", KakaoLoginView.as_view(), name="kakao_token"),
    path("nickname/", NicknameUpdateView.as_view(), name="nickname_update"),
    path("password/", PasswordChangeView.as_view(), name="password_change"),
    path("password/reset/", PasswordResetView.as_view(), name="password_reset"),
    path("email/check/", EmailCheckView.as_view(), name="email_check"),
    path("email/password/reset/", EmailPasswordResetView.as_view(), name="email_password_reset"),
    path("account/", PhoneNumberFindAccountView.as_view(), name="find_account"),
    path("phone/account-info/", PhoneNumberAccountInfoView.as_view(), name="phone_account_info"),
    path("mypage/", MyPageUserInfoView.as_view(), name="mypage_user_info"),
]
