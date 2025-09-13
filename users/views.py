import requests
from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiExample

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

        response = Response({
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
        
        # refresh token을 쿠키로 설정
        response.set_cookie(
            'refresh_token',
            str(refresh),
            httponly=True,      # XSS 방지
            secure=False,       # HTTP에서 테스트 (HTTPS에서는 True)
            samesite='Strict',  # CSRF 방지
            max_age=14*24*60*60  # 14일
        )
        
        return response

class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="로그아웃",
        description="사용자를 로그아웃합니다. refresh 토큰 쿠키를 삭제합니다.",
        request=None,  # body 없음, 쿠키로만 처리
        responses={
            200: {
                'description': '로그아웃 성공',
                'examples': {
                    'application/json': {
                        'success': True,
                        'message': '로그아웃되었습니다.'
                    }
                }
            },
            400: {
                'description': '잘못된 요청 데이터',
                'examples': {
                    'application/json': {
                        'error': '로그아웃 실패'
                    }
                }
            },
            401: {'description': '인증되지 않은 사용자'}
        },
        tags=['인증']
    )
    def post(self, request):
        try:
            # 쿠키에서 refresh token 가져오기
            refresh_token = request.COOKIES.get('refresh_token')
            
            if not refresh_token:
                return Response({"error": "refresh 토큰 쿠키가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            
            # refresh token 유효성 검사
            try:
                refresh_token_obj = RefreshToken(refresh_token)
                user_id = refresh_token_obj['user_id']
            except Exception as e:
                return Response({"error": f"유효하지 않은 refresh 토큰입니다: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 로그아웃 성공 - refresh token 쿠키만 삭제
            response = Response({
                "success": True, 
                "message": "로그아웃되었습니다. refresh token 쿠키가 삭제되었습니다."
            }, status=status.HTTP_200_OK)
            
            # refresh token 쿠키 삭제
            response.delete_cookie(
                'refresh_token',
                path='/',
                domain=None,
                samesite='Strict'
            )
            
            return response
            
        except Exception as e:
            return Response({"error": f"로그아웃 실패: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

