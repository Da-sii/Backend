from django.urls import path
from . import verification_views
from . import verification_token_views

urlpatterns = [
    # 전화번호 인증 발송 통합 API (sms)
    path('send/', verification_views.PhoneVerificationView.as_view(), name='phone-verification-send'),
    
    # 인증번호 검증 API (sms)
    path('verify/', verification_views.VerifyCodeView.as_view(), name='verify-code'),

# 인증코드 발급 API (Octomo)
    path('octomo/send/', verification_views.OctomoVerificationView.as_view(), name='octomo-verification-send'),
    
    # 인증 토큰 검증 API
    path('token/verify/', verification_token_views.VerificationTokenView.as_view(), name='verify-token'),
    
    # 계정 삭제 정보 HTML 페이지 (구글 배포 규정)
    path('delete-info/', verification_views.DeleteInfoView.as_view(), name='delete-info'),
]
