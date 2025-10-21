from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
import logging
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.openapi import OpenApiResponse

from users.models import User
from users.utils import generate_jwt_tokens_with_metadata
from socials.serializers import AppleSigninSerializer
from socials.utils import verify_identity_token

logger = logging.getLogger(__name__)

# Create your views here.
class AppleSigninView(GenericAPIView):
    serializer_class = AppleSigninSerializer
    permission_classes = [AllowAny]  # 인증 없이 접근 가능

    @extend_schema(
        summary="Apple 로그인",
        description="Apple Sign-In을 통해 사용자 인증을 처리합니다.",
        tags=["소셜 로그인"],
        request=AppleSigninSerializer,
        examples=[
            OpenApiExample(
                'Apple 로그인 요청',
                value={
                    "identityToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkpNUjNENVJNVFJZQVoiLCJ0eXAiOiJKV1QifQ..."
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(
                description='로그인 성공',
                examples=[
                    OpenApiExample(
                        '기존 사용자 로그인',
                        value={
                            "success": True,
                            "message": "Apple 로그인 성공",
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "nickname": "user123456",
                                "is_new_user": False
                            },
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                        }
                    ),
                    OpenApiExample(
                        '신규 사용자 가입 및 로그인',
                        value={
                            "success": True,
                            "message": "Apple 회원가입 및 로그인 성공",
                            "user": {
                                "id": 2,
                                "email": "newuser@apple.com",
                                "nickname": "user789012",
                                "is_new_user": True
                            },
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='토큰 검증 실패',
                examples=[
                    OpenApiExample(
                        '토큰 검증 실패',
                        value={
                            "success": False,
                            "message": "토큰 검증 실패: 유효하지 않은 토큰입니다"
                        }
                    )
                ]
            )
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identity_token = serializer.validated_data["identityToken"]
        
        try:
            # Apple 토큰 검증
            payload = verify_identity_token(identity_token)
            logger.info(f"Apple 토큰 검증 성공 - apple_id: {payload.get('sub')}")
                
        except Exception as e:
            logger.error(f"Apple 토큰 검증 실패: {str(e)}")
            return Response(
                {
                    "success": False,
                    "message": f"토큰 검증 실패: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apple ID 및 이메일 추출
        apple_id = payload["sub"]
        email = payload.get("email")
        
        # 이메일이 없으면 Apple ID로 생성
        if not email:
            email = f"{apple_id}@apple.privaterelay.appleid.com"
        
        # 사용자 생성 또는 조회
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "apple": True,
                "nickname": User.objects.generate_nickname(),
            },
        )
        
        # 기존 사용자라면 Apple 로그인 플래그 업데이트
        if not created and not user.apple:
            user.apple = True
            user.save()

        # JWT 토큰 발급 (apple 타입으로 메타데이터 추가)
        tokens = generate_jwt_tokens_with_metadata(user, 'apple')

        response_data = {
            "success": True,
            "message": "Apple 로그인 성공" if not created else "Apple 회원가입 및 로그인 성공",
            "user": {
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "is_new_user": created,
            },
            "access": tokens['access'],
        }

        response = Response(response_data, status=status.HTTP_200_OK)
        
        # refresh token을 쿠키로 설정
        response.set_cookie(
            'refresh_token',
            tokens['refresh'],
            httponly=True,      # XSS 방지
            secure=settings.DJANGO_ENV == "production",  # 프로덕션에서는 HTTPS 필수
            samesite='Strict',  # CSRF 방지
            max_age=14*24*60*60  # 14일
        )
        
        logger.info(f"Apple 로그인 완료 - 사용자: {user.email}, 새 사용자: {created}")
        return response
