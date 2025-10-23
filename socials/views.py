from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
import logging
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.openapi import OpenApiResponse

from users.models import User
from users.utils import generate_jwt_tokens_with_metadata
from socials.serializers import AppleSigninSerializer, AdvertisementInquirySerializer
from socials.utils import verify_identity_token, send_advertisement_inquiry_email

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


class AdvertisementInquiryView(GenericAPIView):
    """광고/제휴 문의 API"""
    serializer_class = AdvertisementInquirySerializer
    permission_classes = [AllowAny]  # 인증 없이 접근 가능
    
    @extend_schema(
        summary="광고/제휴 문의 접수",
        description="광고 및 제휴 문의를 접수하고 관리자에게 이메일을 전송합니다.",
        tags=["광고/제휴 문의"],
        request=AdvertisementInquirySerializer,
        examples=[
            OpenApiExample(
                '광고 문의 접수',
                value={
                    "inquiry_type": "domestic",
                    "brand_name": "샘플 브랜드",
                    "launch_status": "launched",
                    "inquiry_content": "다시 앱에 광고를 진행하고 싶습니다. 제품 소개 및 마케팅 전략에 대해 상담하고 싶습니다.",
                    "name": "홍길동",
                    "contact_number": "010-1234-5678",
                    "email": "hong@example.com"
                },
                request_only=True,
                description=(
                    "inquiry_type:\n"
                    "  - domestic (국내 광고 문의)\n"
                    "  - global (글로벌 광고 문의)\n"
                    "  - other (기타 문의)\n"
                    "\n"
                    "launch_status:\n"
                    "  - launched (출시 완료)\n"
                    "  - within_1_month (미출시 1개월 내)\n"
                    "  - within_3_months (미출시 3개월 내)\n"
                    "  - over_3_months (미출시 3개월 이상)"
                )
            )
        ],
        responses={
            201: OpenApiResponse(
                description='문의 접수 성공',
                examples=[
                    OpenApiExample(
                        '문의 접수 성공',
                        value={
                            "success": True,
                            "message": "문의가 성공적으로 접수되었습니다. 담당자가 확인 후 1영업일 내에 연락드릴 예정입니다.",
                            "inquiry_id": 1
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='입력 데이터 오류',
                examples=[
                    OpenApiExample(
                        '유효성 검사 실패',
                        value={
                            "success": False,
                            "message": "입력 데이터를 확인해주세요.",
                            "errors": {
                                "inquiry_content": ["문의 내용은 최소 20자 이상 입력해주세요."]
                            }
                        }
                    )
                ]
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # 유효한 데이터를 딕셔너리로 가져오기
            inquiry_data = serializer.validated_data
            
            # 이메일 전송
            email_sent = send_advertisement_inquiry_email(inquiry_data)
            
            if email_sent:
                logger.info(f"광고/제휴 문의 접수 완료 - 브랜드: {inquiry_data['brand_name']}")
                return Response({
                    "success": True,
                    "message": "문의가 성공적으로 접수되었습니다. 담당자가 확인 후 1영업일 내에 연락드릴 예정입니다."
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"광고/제휴 문의 이메일 전송 실패 - 브랜드: {inquiry_data['brand_name']}")
                return Response({
                    "success": False,
                    "message": "이메일 전송에 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                "success": False,
                "message": "입력 데이터를 확인해주세요.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
