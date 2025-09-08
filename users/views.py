import json
import requests
from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import User
from .serializers import SignUpSerializer, SignInSerializer, KakaoLoginSerializer


class SignUpView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = [AllowAny] # 인증 필요 없음 (누구나 회원가입 가능)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # serializer 안의 validate_* 메서드들이 실행됨
        user = serializer.save() # User 생성

        # 토큰 발급
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        return Response(
            {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
            },
            "access": access,
            "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )

class SignInView(GenericAPIView):
    permission_classes = [AllowAny] # 인증 필요 없음 (누구나 회원가입 가능)
    serializer_class = SignInSerializer

    def post(self, request):
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        return Response(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nickname": user.nickname,
                },
                "access": access,
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )

class KakaoLoginView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = KakaoLoginSerializer
    
    @extend_schema(
        summary="카카오 로그인",
        description="카카오 OAuth를 통한 로그인/회원가입",
        request=KakaoLoginSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "nickname": {"type": "string"},
                            "email": {"type": "string"},
                            "kakao": {"type": "boolean"}
                        }
                    },
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                    "message": {"type": "string"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "detail": {"type": "object"}
                }
            }
        },
        tags=["인증"]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        # 1) 토큰 발급
        token_response = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_REST_API_KEY,
                "redirect_uri": settings.KAKAO_REDIRECT_URI,
                "code": code,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5,
        )
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        if not access_token:
            return Response(
                {"error": "Failed to get access token", "detail": token_json}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) 사용자 정보
        profile_response = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        profile_json = profile_response.json()
        
        kakao_id = profile_json.get("id")
        kakao_account = profile_json.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        email = kakao_account.get("email")
        nickname = profile.get("nickname", "")

        if not kakao_id:
            return Response({"error": "Missing kakao_id"}, status=status.HTTP_400_BAD_REQUEST)

        # 이메일 기반 가입/로그인 정책: email이 없으면 400으로 안내
        if not email:
            return Response({
                "error": "Email consent required",
                "detail": {
                    "message": "카카오 동의항목에서 이메일을 선택(또는 필수)로 설정하고, 기존 연결을 해제한 뒤 다시 로그인해야 합니다.",
                    "tips": [
                        "개발자 콘솔 > 카카오 로그인 > 동의항목에서 '카카오계정(이메일)' 활성화",
                        "테스트 계정을 '팀원'으로 추가 후 재로그인",
                        "기존 연결 해제(https://developers.kakao.com/tool/unlink) 후 다시 시도"
                    ]
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3) 이메일로 사용자 조회/갱신
        try:
            user = User.objects.get(email=email)
            if not user.kakao:
                user.kakao = True
                user.save(update_fields=["kakao"])
            created = False
        except User.DoesNotExist:
            # 비밀번호는 건드리지 않는 정책 → set_unusable_password 사용 안 함
            user = User.objects.create_user(
                email=email,
                nickname=nickname or f"kakao_{kakao_id}",
                kakao=True,
            )
            created = True

        # 4) JWT 토큰 발급 (세션 로그인 대신)
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        return Response({
            "success": True,
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "email": user.email,
                "kakao": user.kakao,
            },
            "access": access,
            "refresh": str(refresh),
            "message": "Login successful" if not created else "User created and logged in",
        }, status=status.HTTP_200_OK)
