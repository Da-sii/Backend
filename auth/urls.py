from django.urls import path
from . import verification_views
from . import verification_token_views

urlpatterns = [
    # 전화번호 인증 발송 통합 API
    path('send/', verification_views.PhoneVerificationView.as_view(), name='phone-verification-send'),
    
    # 인증번호 검증 API
    path('verify/', verification_views.VerifyCodeView.as_view(), name='verify-code'),
    
    # 인증 토큰 검증 API
    path('token/verify/', verification_token_views.VerificationTokenView.as_view(), name='verify-token'),
]
