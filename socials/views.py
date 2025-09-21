from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from users.utils import generate_jwt_tokens_with_metadata
from socials.serializers import AppleSigninSerializer
from socials.utils import verify_identity_token

# Create your views here.
class AppleSigninView(GenericAPIView):
    serializer_class = AppleSigninSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identityToken = serializer.validated_data["identityToken"]
        
        try:
            payload = verify_identity_token(identityToken)
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"토큰 검증 실패: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        appleId = payload["sub"]
        email = payload.get("email", f"{appleId}@apple.com")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "apple": True,
                "nickname": User.objects.generate_nickname(),
            },
        )

        # JWT 토큰 발급 (apple 타입으로 메타데이터 추가)
        tokens = generate_jwt_tokens_with_metadata(user, 'apple')

        response = Response(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nickname": user.nickname,
                },
                "access": tokens['access'],
            }, 
            status=status.HTTP_200_OK,
        )
        
        # refresh token을 쿠키로 설정
        response.set_cookie(
            'refresh_token',
            tokens['refresh'],
            httponly=True,      # XSS 방지
            secure=False,       # HTTP에서 테스트 (HTTPS에서는 True)
            samesite='Strict',  # CSRF 방지
            max_age=14*24*60*60  # 14일
        )
        
        return response
