import requests
from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.db import models
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import (
    SignUpSerializer, 
    SignInSerializer, 
    KakaoLoginSerializer,
    KakaoLogoutRequestSerializer,
    UserDeleteRequestSerializer,
    UserDeleteResponseSerializer,
    NicknameUpdateRequestSerializer,
    NicknameUpdateResponseSerializer,
    PasswordVerifyRequestSerializer,
    PasswordVerifyResponseSerializer,
    PasswordChangeRequestSerializer,
    PasswordChangeResponseSerializer,
    PasswordResetRequestSerializer,
    PasswordResetResponseSerializer,
    EmailCheckRequestSerializer,
    EmailCheckResponseSerializer,
    EmailPasswordResetRequestSerializer,
    EmailPasswordResetResponseSerializer,
    PhoneNumberFindAccountResponseSerializer,
    PhoneNumberAccountInfoRequestSerializer,
    PhoneNumberAccountInfoResponseSerializer,
    MyPageUserInfoResponseSerializer
)
from .utils import generate_jwt_tokens_with_metadata, get_token_type_from_token

class SignUpView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = [AllowAny] # 인증 필요 없음 (누구나 회원가입 가능)
    authentication_classes = []  # 인증 클래스를 비워서 토큰 검증을 완전히 비활성화

    @extend_schema(
        summary="회원가입",
        description="이메일과 비밀번호로 회원가입합니다. 회원가입 시 자동으로 로그인되며 access 토큰과 refresh 토큰(쿠키)이 발급됩니다.",
        request=SignUpSerializer,
        examples=[
            OpenApiExample(
                '회원가입 요청',
                value={
                    "email": "user@example.com",
                    "password": "Test1234!",
                    "password2": "Test1234!",
                    "phoneNumber": "010-1234-5678"
                },
                request_only=True
            )
        ],
        responses={
            201: OpenApiResponse(
                description='회원가입 성공',
                examples=[
                    OpenApiExample(
                        '회원가입 성공',
                        value={
                            "success": True,
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "nickname": "user123456",
                                "phoneNumber": "010-1234-5678"
                            },
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='회원가입 실패',
                examples=[
                    OpenApiExample(
                        '이메일 중복',
                        value={
                            "email": ["이미 사용 중인 이메일입니다."]
                        }
                    ),
                    OpenApiExample(
                        '비밀번호 불일치',
                        value={
                            "non_field_errors": ["비밀번호가 일치하지 않습니다."]
                        }
                    ),
                    OpenApiExample(
                        '비밀번호 규칙 위반',
                        value={
                            "password": ["비밀번호는 영문,숫자,특수문자를 모두 포함해야 합니다."]
                        }
                    )
                ]
            )
        },
        tags=['인증']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # serializer 안의 validate_* 메서드들이 실행됨
        user = serializer.save() # User 생성

        # 토큰 발급 (email 타입으로 메타데이터 추가)
        tokens = generate_jwt_tokens_with_metadata(user, 'email')

        response = Response(
            {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "phoneNumber": user.phone_number,
            },
            "access": tokens['access'],
            },
            status=status.HTTP_201_CREATED,
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

class SignInView(GenericAPIView):
    permission_classes = [AllowAny] # 인증 필요 없음 (누구나 회원가입 가능)
    serializer_class = SignInSerializer
    authentication_classes = []  # 인증 클래스를 비워서 토큰 검증을 완전히 비활성화

    @extend_schema(
        summary="로그인",
        description="이메일과 비밀번호로 로그인합니다. 성공 시 access 토큰과 refresh 토큰(쿠키)이 발급됩니다.",
        request=SignInSerializer,
        examples=[
            OpenApiExample(
                '로그인 요청',
                value={
                    "email": "user@example.com",
                    "password": "Test1234!"
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(
                description='로그인 성공',
                examples=[
                    OpenApiExample(
                        '로그인 성공',
                        value={
                            "success": True,
                            "user": {
                                "id": 1,
                                "email": "user@example.com",
                                "nickname": "user123456",
                                "phoneNumber": "010-1234-5678"
                            },
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='로그인 실패',
                examples=[
                    OpenApiExample(
                        '이메일 또는 비밀번호 오류',
                        value={
                            "non_field_errors": ["이메일 또는 비밀번호가 올바르지 않습니다."]
                        }
                    )
                ]
            )
        },
        tags=['인증']
    )
    def post(self, request):
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # 토큰 발급 (email 타입으로 메타데이터 추가)
        tokens = generate_jwt_tokens_with_metadata(user, 'email')

        response = Response(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nickname": user.nickname,
                    "phoneNumber": user.phone_number,
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

class KakaoLoginView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = KakaoLoginSerializer
    authentication_classes = []  # 인증 클래스를 비워서 토큰 검증을 완전히 비활성화

    @extend_schema(
        summary="카카오 로그인",
        description="카카오 로그인을 지원합니다. 두 가지 방식을 지원합니다: 1) SDK 방식: kakao_access_token 전달, 2) Code 방식: 카카오 인증 후 받은 code 전달. 이메일이 없으면 실패하며, 신규 사용자는 자동으로 가입됩니다.",
        request=KakaoLoginSerializer,
        examples=[
            OpenApiExample(
                'SDK 방식 (토큰 직접 전달)',
                value={
                    "kakao_access_token": "카카오_SDK에서_받은_access_token",
                    "kakao_refresh_token": "카카오_SDK에서_받은_refresh_token"
                },
                request_only=True
            ),
            OpenApiExample(
                'Code 방식 (인증 코드 전달)',
                value={
                    "code": "카카오_OAuth_인증_후_받은_code"
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(
                description='카카오 로그인 성공',
                examples=[
                    OpenApiExample(
                        '기존 사용자 로그인',
                        value={
                            "success": True,
                            "user": {
                                "id": 1,
                                "nickname": "카카오사용자",
                                "email": "kakao@example.com",
                                "kakao": True
                            },
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                            "is_new_user": "false",
                            "message": "Login successful"
                        }
                    ),
                    OpenApiExample(
                        '신규 사용자 가입 및 로그인',
                        value={
                            "success": True,
                            "user": {
                                "id": 2,
                                "nickname": "kakao_123456789",
                                "email": "newuser@kakao.com",
                                "kakao": True
                            },
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                            "is_new_user": "true",
                            "message": "User created and logged in"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='카카오 로그인 실패',
                examples=[
                    OpenApiExample(
                        '이메일 동의 필요',
                        value={
                            "error": "Email consent required",
                            "detail": {
                                "message": "카카오 동의항목에서 이메일을 선택(또는 필수)로 설정하고, 기존 연결을 해제한 뒤 다시 로그인해야 합니다.",
                                "tips": [
                                    "개발자 콘솔 > 카카오 로그인 > 동의항목에서 '카카오계정(이메일)' 활성화",
                                    "테스트 계정을 '팀원'으로 추가 후 재로그인",
                                    "기존 연결 해제(https://developers.kakao.com/tool/unlink) 후 다시 시도"
                                ]
                            }
                        }
                    )
                ]
            )
        },
        tags=['인증']
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        kakao_access_token = serializer.validated_data.get("kakao_access_token", "").strip()
        kakao_refresh_token = serializer.validated_data.get("kakao_refresh_token", "").strip()
        code = serializer.validated_data.get("code", "").strip()
        
        # Code 방식인 경우 토큰 교환
        if code:
            try:
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
                
                if token_response.status_code != 200:
                    try:
                        error_detail = token_response.json()
                    except (ValueError, AttributeError):
                        error_detail = token_response.text if token_response.text else "카카오 토큰 교환 실패"
                    
                    return Response(
                        {
                            "error": "Failed to exchange code for token",
                            "detail": error_detail,
                            "status_code": token_response.status_code
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                token_json = token_response.json()
                kakao_access_token = token_json.get("access_token")
                kakao_refresh_token = token_json.get("refresh_token")
                
                if not kakao_access_token:
                    return Response(
                        {"error": "Failed to get access token", "detail": token_json}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except requests.exceptions.RequestException as e:
                return Response(
                    {
                        "error": "카카오 토큰 교환 실패",
                        "detail": f"네트워크 오류 또는 타임아웃: {str(e)}"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # kakao_access_token이 없으면 에러
        if not kakao_access_token:
            return Response(
                {
                    "error": "카카오 액세스 토큰이 필요합니다",
                    "detail": "kakao_access_token 또는 code를 제공해주세요."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 카카오 access_token으로 사용자 정보 조회
        try:
            profile_response = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {kakao_access_token}"},
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            return Response(
                {
                    "error": "카카오 API 호출 실패",
                    "detail": f"네트워크 오류 또는 타임아웃: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 카카오 API 호출 실패 처리
        if profile_response.status_code != 200:
            try:
                error_detail = profile_response.json()
            except (ValueError, AttributeError):
                error_detail = profile_response.text if profile_response.text else "카카오 사용자 정보 조회 실패"
            
            return Response(
                {
                    "error": "Failed to get user info from Kakao",
                    "detail": error_detail,
                    "status_code": profile_response.status_code
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # JSON 파싱
        try:
            profile_json = profile_response.json()
        except (ValueError, AttributeError) as e:
            return Response(
                {
                    "error": "카카오 응답 파싱 실패",
                    "detail": f"카카오 API 응답을 JSON으로 파싱할 수 없습니다: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
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

        existing_user = User.objects.filter(email=email).first()
        is_new_user = existing_user is None

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

        # 4) JWT 토큰 발급 (kakao 타입으로 메타데이터 추가)
        tokens = generate_jwt_tokens_with_metadata(
            user,
            'kakao',
            kakao_access_token=kakao_access_token,
            kakao_refresh_token=kakao_refresh_token,
        )

        response = Response({
            "success": True,
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "email": user.email,
                "kakao": user.kakao,
            },
            "access": tokens['access'],
            "is_new_user": is_new_user,
            "message": "Login successful" if not created else "User created and logged in",
        }, status=status.HTTP_200_OK)
        
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
        # 로그아웃 응답 생성
        response = Response({
            "success": True, 
            "message": "로그아웃되었습니다. refresh token 쿠키가 삭제되었습니다."
        }, status=status.HTTP_200_OK)
        
        # refresh token 쿠키 삭제 (쿠키가 없어도 에러 없이 처리)
        response.delete_cookie(
            'refresh_token',
            path='/'
        )
        
        return response

class TokenRefreshView(GenericAPIView):
    """쿠키 기반 토큰 리프레시"""
    permission_classes = [AllowAny]
    authentication_classes = []  # 인증 없이 사용 가능

    @extend_schema(
        summary="Access 토큰 재발급",
        description="쿠키에 저장된 refresh 토큰을 사용하여 새로운 access 토큰을 발급합니다. body 없이 쿠키만으로 처리됩니다.",
        request=None,  # body 없음
        responses={
            200: OpenApiResponse(
                description='토큰 재발급 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            'success': True,
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='토큰 재발급 실패',
                examples=[
                    OpenApiExample(
                        'refresh 토큰 없음',
                        value={
                            'error': 'refresh 토큰이 제공되지 않았습니다.'
                        }
                    ),
                    OpenApiExample(
                        '유효하지 않은 토큰',
                        value={
                            'error': '유효하지 않거나 만료된 refresh 토큰입니다.'
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='사용자를 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '사용자 없음',
                        value={
                            'error': '토큰에 해당하는 사용자를 찾을 수 없습니다.'
                        }
                    )
                ]
            )
        },
        tags=['인증']
    )
    def post(self, request):
        """
        쿠키에서 refresh 토큰을 가져와 새로운 access 토큰을 발급합니다.
        """
        # 쿠키에서 refresh 토큰 가져오기
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'refresh 토큰이 제공되지 않았습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # refresh 토큰 검증 및 새 access 토큰 생성
            refresh = RefreshToken(refresh_token)
            
            # 토큰에서 사용자 ID 추출
            user_id = refresh.get('user_id')
            
            # 사용자 존재 여부 확인
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': '토큰에 해당하는 사용자를 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 새로운 access 토큰 발급
            access_token = str(refresh.access_token)
            
            return Response({
                'success': True,
                'access': access_token
            }, status=status.HTTP_200_OK)
            
        except TokenError as e:
            return Response(
                {'error': f'유효하지 않거나 만료된 refresh 토큰입니다: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'토큰 재발급 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class KakaoLogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = KakaoLogoutRequestSerializer
    
    @extend_schema(
        summary="카카오 로그아웃",
        description="카카오 계정 사용자의 서버 로그아웃을 처리합니다. 카카오 로그아웃은 프론트엔드에서 window.Kakao.Auth.logout()으로 처리해주세요.",
        request=KakaoLogoutRequestSerializer,
        examples=[
            OpenApiExample(
                '요청 예시 (body 없음)',
                value={},
                request_only=True
            ),
            OpenApiExample(
                '요청 예시 (카카오 토큰 포함)',
                value={
                    "kakao_access_token": "카카오에서_발급받은_access_token"
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(
                description='카카오 로그아웃 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            'success': True,
                            'message': '카카오 로그아웃이 완료되었습니다.'
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='카카오 로그아웃 실패',
                examples=[
                    OpenApiExample(
                        '카카오 계정이 아닌 경우',
                        value={
                            'error': '카카오 계정이 아닙니다.'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '토큰 없음',
                        value={
                            'detail': 'Authentication credentials were not provided.'
                        }
                    )
                ]
            )
        },
        tags=['인증']
    )
    def post(self, request):
        """
        카카오 계정 로그아웃과 서버 로그아웃을 처리합니다.
        """
        user = request.user
        
        # 카카오 사용자인지 확인
        if not user.kakao:
            return Response({
                'error': '카카오 계정이 아닙니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 카카오 access_token이 제공된 경우 카카오 로그아웃 API 호출
        kakao_access_token = request.data.get('kakao_access_token')
        if kakao_access_token:
            try:
                kakao_logout_response = requests.post(
                    "https://kapi.kakao.com/v1/user/logout",
                    headers={"Authorization": f"Bearer {kakao_access_token}"},
                    timeout=5,
                )
                if kakao_logout_response.status_code != 200:
                    print(f"카카오 로그아웃 API 오류: {kakao_logout_response.text}")
            except Exception as e:
                print(f"카카오 로그아웃 처리 중 오류: {str(e)}")
        
        # 서버 로그아웃 처리 (refresh token 쿠키 삭제)
        response = Response({
            "success": True, 
            "message": "카카오 로그아웃이 완료되었습니다."
        }, status=status.HTTP_200_OK)
        
        # refresh token 쿠키 삭제
        response.delete_cookie(
            'refresh_token',
            path='/'
        )
        
        return response

class UserDeleteView(GenericAPIView):
    """회원탈퇴 API"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserDeleteRequestSerializer
    
    @extend_schema(
        summary="회원탈퇴",
        description="현재 로그인한 사용자의 계정을 완전히 삭제합니다. 카카오/애플 연동 계정인 경우 해당 서비스에서도 탈퇴 처리합니다.",
        request=UserDeleteRequestSerializer,
        examples=[
            OpenApiExample(
                '일반 사용자 탈퇴',
                value={},
                request_only=True
            ),
            OpenApiExample(
                '카카오 사용자 탈퇴',
                value={
                    "kakao_access_token": "카카오에서_발급받은_access_token"
                },
                request_only=True
            ),
            OpenApiExample(
                '애플 사용자 탈퇴',
                value={
                    "apple_user_id": "애플_사용자_ID"
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(
                response=UserDeleteResponseSerializer,
                description='회원탈퇴 성공',
                examples=[
                    OpenApiExample(
                        '탈퇴 성공',
                        value={
                            "success": True,
                            "message": "회원탈퇴가 완료되었습니다.",
                            "deleted_user_id": 1,
                            "deleted_email": "user@example.com"
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='회원탈퇴 실패',
                examples=[
                    OpenApiExample(
                        '카카오 토큰 필요',
                        value={
                            "error": "카카오 사용자는 kakao_access_token이 필요합니다."
                        }
                    ),
                    OpenApiExample(
                        '애플 사용자 ID 필요',
                        value={
                            "error": "애플 사용자는 apple_user_id가 필요합니다."
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '토큰 없음',
                        value={
                            "detail": "Authentication credentials were not provided."
                        }
                    )
                ]
            )
        },
        tags=['계정 관리']
    )
    def delete(self, request):
        """
        현재 로그인한 사용자의 계정을 완전히 삭제합니다.
        """
        user = request.user
        
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 사용자 정보 저장 (삭제 후 응답에 사용)
        user_id = user.id
        user_email = user.email
        
        # 카카오 사용자인 경우 카카오 탈퇴 처리
        if user.kakao:
            # 1순위: 요청 바디의 kakao_access_token
            kakao_access_token = request.data.get('kakao_access_token')

            # 2순위: 클라이언트가 보내온 refresh/access JWT 안에 들어 있는 kakao 토큰 사용
            # 프론트가 회원탈퇴 요청 시, 본인이 갖고 있는 refresh 토큰을 같이 보내준다고 가정
            if not kakao_access_token:
                from .utils import get_kakao_tokens_from_token

                # 요청 바디에서 refresh 토큰 우선 사용
                refresh_token_string = request.data.get('refresh')

                # 바디에 refresh가 없다면, Authorization 헤더(access 토큰)에서도 시도
                token_string = None
                if refresh_token_string:
                    token_string = refresh_token_string
                else:
                    auth_header = request.headers.get('Authorization')
                    if auth_header and auth_header.startswith('Bearer '):
                        token_string = auth_header.split(' ', 1)[1]

                if token_string:
                    kakao_tokens = get_kakao_tokens_from_token(token_string)
                    if kakao_tokens and kakao_tokens.get('kakao_access_token'):
                        kakao_access_token = kakao_tokens['kakao_access_token']

            # 위 과정까지 했는데도 카카오 토큰이 없으면 오류 반환
            if not kakao_access_token:
                return Response({
                    'error': '카카오 사용자는 kakao_access_token 또는 JWT(access/refresh)에 포함된 카카오 토큰이 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                # 카카오 연결 끊기 API 호출
                kakao_unlink_response = requests.post(
                    "https://kapi.kakao.com/v1/user/unlink",
                    headers={"Authorization": f"Bearer {kakao_access_token}"},
                    timeout=5,
                )
                if kakao_unlink_response.status_code != 200:
                    print(f"카카오 연결 끊기 API 오류: {kakao_unlink_response.text}")
                    # 카카오 API 오류가 있어도 서버에서는 탈퇴 진행
            except Exception as e:
                print(f"카카오 연결 끊기 처리 중 오류: {str(e)}")
                # 카카오 API 오류가 있어도 서버에서는 탈퇴 진행
        
        # 애플 사용자인 경우 애플 탈퇴 처리
        if user.apple:
            apple_user_id = request.data.get('apple_user_id')
            if not apple_user_id:
                return Response({
                    'error': '애플 사용자는 apple_user_id가 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 애플 탈퇴는 일반적으로 클라이언트에서 처리
            # 서버에서는 사용자 정보만 삭제
            print(f"애플 사용자 탈퇴: {apple_user_id}")
        
        # 사용자 및 관련 데이터 완전 삭제
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                # 1. 사용자가 작성한 리뷰 삭제
                cursor.execute("DELETE FROM reviews WHERE user_id = %s", [user_id])
                print(f"리뷰 삭제 완료: user_id={user_id}")
                
                # 2. 사용자가 작성한 댓글 삭제 (있다면)
                try:
                    cursor.execute("DELETE FROM comments WHERE user_id = %s", [user_id])
                    print(f"댓글 삭제 완료: user_id={user_id}")
                except:
                    print("댓글 테이블이 없거나 삭제할 댓글이 없음")
                
                # 3. 사용자가 작성한 기타 관련 데이터 삭제 (필요시 추가)
                # cursor.execute("DELETE FROM other_table WHERE user_id = %s", [user_id])
                
                # 4. 마지막으로 사용자 삭제
                cursor.execute("DELETE FROM users WHERE id = %s", [user_id])
                print(f"사용자 삭제 완료: user_id={user_id}")
            
            response_data = {
                'success': True,
                'message': '회원탈퇴가 완료되었습니다.',
                'deleted_user_id': user_id,
                'deleted_email': user_email
            }
            
            response_serializer = UserDeleteResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'회원탈퇴 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NicknameUpdateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NicknameUpdateRequestSerializer

    @extend_schema(
        summary="닉네임 변경",
        description="현재 로그인한 사용자의 닉네임을 변경합니다.",
        request=NicknameUpdateRequestSerializer,
        responses={
            200: NicknameUpdateResponseSerializer,
            400: {
                'description': '유효성 오류',
                'examples': {'application/json': {'nickname': ['이미 사용 중인 닉네임입니다.']}}
            },
            401: {'description': '인증 필요'}
        },
    )
    def patch(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.nickname = serializer.validated_data['nickname']
        request.user.save(update_fields=['nickname'])

        response_data = {
            'success': True,
            'user_id': request.user.id,
            'nickname': request.user.nickname
        }
        response_serializer = NicknameUpdateResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

class PasswordVerifyView(GenericAPIView):
    """현재 비밀번호 확인 API"""
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordVerifyRequestSerializer

    @extend_schema(
        summary="현재 비밀번호 확인",
        description="현재 로그인한 사용자의 비밀번호가 올바른지 확인합니다.",
        request=PasswordVerifyRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=PasswordVerifyResponseSerializer,
                description='비밀번호 확인 완료',
                examples=[
                    OpenApiExample(
                        '비밀번호 일치',
                        value={
                            "success": True,
                            "valid": True,
                            "message": "비밀번호가 일치합니다."
                        }
                    ),
                    OpenApiExample(
                        '비밀번호 불일치',
                        value={
                            "success": True,
                            "valid": False,
                            "message": "비밀번호가 일치하지 않습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청',
                examples=[
                    OpenApiExample(
                        '비밀번호 누락',
                        value={
                            "current_password": ["현재 비밀번호를 입력해주세요."]
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자'
            )
        },
        tags=['사용자 관리']
    )
    def post(self, request):
        """
        현재 사용자의 비밀번호가 올바른지 확인합니다.
        """
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 비밀번호 확인
        current_password = serializer.validated_data['current_password']
        is_valid = request.user.check_password(current_password)
        
        response_data = {
            'success': True,
            'valid': is_valid,
            'message': '비밀번호가 일치합니다.' if is_valid else '비밀번호가 일치하지 않습니다.'
        }
        
        response_serializer = PasswordVerifyResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class PasswordChangeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeRequestSerializer

    @extend_schema(
        summary="비밀번호 변경",
        description="현재 사용자의 비밀번호를 변경합니다. (email 로그인 사용자만 가능)",
        request=PasswordChangeRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=PasswordChangeResponseSerializer,
                description='비밀번호 변경 성공',
                examples=[
                    OpenApiExample(
                        '비밀번호 변경 성공',
                        value={
                            "success": True,
                            "user_id": 1,
                            "message": "비밀번호가 성공적으로 변경되었습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='비밀번호 변경 실패',
                examples=[
                    OpenApiExample(
                        '소셜 로그인 사용자',
                        value={
                            "error": "소셜 로그인 사용자는 비밀번호를 변경할 수 없습니다.",
                            "detail": "카카오 또는 애플 로그인 사용자는 비밀번호 변경이 불가능합니다.",
                            "current_token_type": "kakao"
                        }
                    ),
                    OpenApiExample(
                        '현재 비밀번호 불일치',
                        value={
                            "current_password": ["현재 비밀번호가 올바르지 않습니다."]
                        }
                    ),
                    OpenApiExample(
                        '새 비밀번호 규칙 위반',
                        value={
                            "new_password1": ["비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다."]
                        }
                    ),
                    OpenApiExample(
                        '새 비밀번호 불일치',
                        value={
                            "non_field_errors": ["새 비밀번호가 일치하지 않습니다."]
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자'
            )
        },
        tags=['사용자 관리']
    )
    def post(self, request):
        """
        현재 사용자의 비밀번호를 변경합니다.
        (email 로그인 사용자만 가능)
        """
        # JWT 토큰에서 tokenType 확인
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return Response(
                {"error": "Authorization header가 없습니다."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        access_token = auth_header.split(' ')[1]
        token_type = get_token_type_from_token(access_token)
        
        # tokenType이 'email'이 아니면 비밀번호 변경 불가
        if token_type != 'email':
            return Response(
                {
                    "error": "소셜 로그인 사용자는 비밀번호를 변경할 수 없습니다.",
                    "detail": "카카오 또는 애플 로그인 사용자는 비밀번호 변경이 불가능합니다.",
                    "current_token_type": token_type
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 현재 비밀번호 확인
        current_password = serializer.validated_data['current_password']
        if not request.user.check_password(current_password):
            return Response(
                {"current_password": ["현재 비밀번호가 올바르지 않습니다."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 새 비밀번호로 변경
        new_password = serializer.validated_data['new_password1']
        request.user.set_password(new_password)
        request.user.save()
        
        response_data = {
            'success': True,
            'user_id': request.user.id,
            'message': '비밀번호가 성공적으로 변경되었습니다.'
        }
        
        response_serializer = PasswordChangeResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class PhoneNumberFindAccountView(GenericAPIView):
    """핸드폰번호로 계정 찾기"""
    permission_classes = [AllowAny]
    authentication_classes = []  # 인증 클래스를 비워서 토큰 검증을 완전히 비활성화

    @extend_schema(
        summary="핸드폰번호로 계정 찾기",
        description="핸드폰번호를 쿼리 파라미터로 입력하여 해당 번호로 등록된 계정들을 찾습니다. access token이 없어도 사용 가능합니다.",
        parameters=[
            OpenApiParameter(
                name='phone_number',
                location=OpenApiParameter.QUERY,
                description='핸드폰번호 (예: 010-1234-5678)',
                required=True,
                type=str,
                pattern=r'^01[0-9]-?\d{3,4}-?\d{4}$'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=PhoneNumberFindAccountResponseSerializer,
                description='계정 찾기 성공',
                examples=[
                    OpenApiExample(
                        '계정 찾기 성공',
                        value={
                            "success": True,
                            "accounts": [
                                {
                                    "id": 1,
                                    "email": "user@example.com",
                                    "nickname": "user123456",
                                    "login_type": "email",
                                    "created_at": "2024-01-15T10:30:00Z"
                                },
                                {
                                    "id": 2,
                                    "email": "kakao@example.com",
                                    "nickname": "kakao_user",
                                    "login_type": "kakao",
                                    "created_at": "2024-01-20T14:45:00Z"
                                }
                            ],
                            "message": "해당 핸드폰번호로 등록된 계정을 찾았습니다."
                        }
                    ),
                    OpenApiExample(
                        '계정 없음',
                        value={
                            "success": True,
                            "accounts": [],
                            "message": "해당 핸드폰번호로 등록된 계정이 없습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청 데이터',
                examples=[
                    OpenApiExample(
                        '핸드폰번호 누락',
                        value={
                            "phone_number": ["핸드폰번호는 필수입니다."]
                        }
                    ),
                    OpenApiExample(
                        '잘못된 핸드폰번호 형식',
                        value={
                            "phone_number": ["올바른 핸드폰번호 형식이 아닙니다. (예: 010-1234-5678)"]
                        }
                    )
                ]
            )
        },
        tags=['계정 관리']
    )
    def get(self, request):
        """핸드폰번호로 등록된 계정들을 찾습니다."""
        phone_number = request.GET.get('phone_number')
        
        if not phone_number:
            return Response(
                {"phone_number": ["핸드폰번호는 필수입니다."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 핸드폰번호 형식 검증
        import re
        phone_pattern = r'^01[0-9]-?\d{3,4}-?\d{4}$'
        if not re.match(phone_pattern, phone_number):
            return Response(
                {"phone_number": ["올바른 핸드폰번호 형식이 아닙니다. (예: 010-1234-5678)"]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 해당 핸드폰번호로 등록된 사용자들 조회
        users = User.objects.filter(phone_number=phone_number)
        
        accounts = []
        for user in users:
            # 로그인 타입 결정
            if user.kakao and user.apple:
                # kakao와 apple 둘 다 True인 경우
                login_type = "kakao_apple"
            elif user.kakao:
                login_type = "kakao"
            elif user.google:
                login_type = "google"
            elif user.apple:
                login_type = "apple"
            else:
                login_type = "email"
            
            accounts.append({
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "login_type": login_type,
                "created_at": user.created_at
            })
        
        if accounts:
            message = f"해당 핸드폰번호로 등록된 계정 {len(accounts)}개를 찾았습니다."
        else:
            message = "해당 핸드폰번호로 등록된 계정이 없습니다."
        
        response_data = {
            'success': True,
            'accounts': accounts,
            'message': message
        }
        
        response_serializer = PhoneNumberFindAccountResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class PhoneNumberAccountInfoView(GenericAPIView):
    """전화번호로 계정 정보 조회 API"""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PhoneNumberAccountInfoRequestSerializer

    @extend_schema(
        summary="전화번호로 계정 정보 조회",
        description="전화번호를 받아서 해당 번호로 가입된 계정들의 이메일과 가입일을 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='phone_number',
                location=OpenApiParameter.QUERY,
                description='전화번호 (다양한 형식 지원: 010-1234-5678, 01012345678, +82-10-1234-5678 등)',
                required=True,
                type=str
            )
        ],
        responses={
            200: OpenApiResponse(
                response=PhoneNumberAccountInfoResponseSerializer,
                description='계정 정보 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시 - 계정 있음',
                        value={
                            "success": True,
                            "phone_number": "01023086047",
                            "accounts": [
                                {
                                    "email": "user1@example.com",
                                    "created_at": "2024-01-15T10:30:00Z"
                                },
                                {
                                    "email": "user2@example.com", 
                                    "created_at": "2024-01-20T15:45:00Z"
                                }
                            ],
                            "message": "총 2개의 계정을 찾았습니다."
                        }
                    ),
                    OpenApiExample(
                        '성공 예시 - 계정 없음',
                        value={
                            "success": True,
                            "phone_number": "01023086047",
                            "accounts": [],
                            "message": "해당 전화번호로 가입된 계정이 없습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청 데이터',
                examples=[
                    OpenApiExample(
                        '전화번호 누락',
                        value={
                            "error": "전화번호가 필요합니다."
                        }
                    )
                ]
            )
        },
        tags=['계정 관리']
    )
    def get(self, request):
        """
        전화번호를 받아서 해당 번호로 가입된 계정들의 정보를 조회합니다.
        """
        from auth.utils import parse_phone_number
        
        # 쿼리 파라미터에서 전화번호 추출
        phone_number = request.query_params.get('phone_number')
        
        if not phone_number:
            return Response(
                {'error': '전화번호가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 전화번호 파싱 (다양한 형식 지원)
        try:
            parsed_phone = parse_phone_number(phone_number)
        except Exception as e:
            return Response(
                {'error': f'전화번호 형식이 올바르지 않습니다: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 전화번호에서 '-' 제거한 형태도 생성
        phone_without_dash = parsed_phone.replace('-', '')
        phone_with_dash = parsed_phone
        
        # 두 가지 형태 모두로 검색 (중복 제거)
        users = User.objects.filter(
            models.Q(phone_number=phone_with_dash) | 
            models.Q(phone_number=phone_without_dash)
        ).distinct().order_by('id')
        
        # 계정 정보 리스트 생성
        accounts = []
        for user in users:
            # date_joined 필드가 있으면 사용, 없으면 None
            created_at = getattr(user, 'date_joined', None)
            accounts.append({
                'email': user.email,
                'created_at': created_at.isoformat() if created_at else None
            })
        
        # 응답 데이터 생성
        response_data = {
            'success': True,
            'phone_number': parsed_phone,
            'accounts': accounts,
            'message': f'총 {len(accounts)}개의 계정을 찾았습니다.' if accounts else '해당 전화번호로 가입된 계정이 없습니다.'
        }
        
        response_serializer = PhoneNumberAccountInfoResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class MyPageUserInfoView(GenericAPIView):
    """마이페이지 사용자 정보 조회"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="마이페이지 사용자 정보 조회",
        description="현재 로그인한 사용자의 마이페이지 정보를 조회합니다. 인증되지 않은 경우에도 200을 반환하며 authenticated: false로 표시됩니다.",
        responses={
            200: OpenApiResponse(
                response=MyPageUserInfoResponseSerializer,
                description='마이페이지 사용자 정보 조회',
                examples=[
                    OpenApiExample(
                        '인증된 사용자',
                        value={
                            "success": True,
                            "authenticated": True,
                            "user_info": {
                                "nickname": "사용자123",
                                "email": "user@example.com",
                                "login_type": "kakao",
                                "review_count": 5
                            }
                        }
                    ),
                    OpenApiExample(
                        '인증되지 않은 사용자',
                        value={
                            "success": True,
                            "authenticated": False,
                            "message": "로그인이 필요합니다."
                        }
                    )
                ]
            )
        },
        tags=['마이페이지']
    )
    def get(self, request):
        """마이페이지 사용자 정보를 조회합니다."""
        from .utils import get_token_type_from_token
        from review.models import Review
        
        # 사용자 인증 여부 확인
        if not request.user.is_authenticated:
            return Response(
                {
                    'success': True,
                    'authenticated': False,
                    'message': '로그인이 필요합니다.'
                },
                status=status.HTTP_200_OK
            )
        
        # JWT 토큰에서 로그인 방식 추출
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            login_type = get_token_type_from_token(token)
        else:
            login_type = 'email'  # 기본값
        
        # 사용자 리뷰 개수 조회
        review_count = Review.objects.filter(user=request.user).count()
        
        # 사용자 정보 구성
        user_info = {
            'nickname': request.user.nickname,
            'email': request.user.email,
            'login_type': login_type,
            'review_count': review_count
        }
        
        response_data = {
            'success': True,
            'authenticated': True,
            'user_info': user_info
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

class PasswordResetView(GenericAPIView):
    """비밀번호 재설정 API (계정 찾기용)"""
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        summary="비밀번호 재설정",
        description="현재 비밀번호를 확인하고 새로운 비밀번호로 변경합니다. 계정 찾기 후 비밀번호 변경용 API입니다.",
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=PasswordResetResponseSerializer,
                description='비밀번호 재설정 성공',
                examples=[
                    OpenApiExample(
                        '비밀번호 재설정 성공',
                        value={
                            "success": True,
                            "user_id": 1,
                            "message": "비밀번호가 성공적으로 재설정되었습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='비밀번호 재설정 실패',
                examples=[
                    OpenApiExample(
                        '현재 비밀번호 불일치',
                        value={
                            "current_password": ["현재 비밀번호가 올바르지 않습니다."]
                        }
                    ),
                    OpenApiExample(
                        '새 비밀번호 규칙 위반',
                        value={
                            "new_password1": ["비밀번호는 영문을 포함해야 합니다."]
                        }
                    ),
                    OpenApiExample(
                        '새 비밀번호 불일치',
                        value={
                            "non_field_errors": ["새 비밀번호가 일치하지 않습니다."]
                        }
                    ),
                    OpenApiExample(
                        '동일한 비밀번호',
                        value={
                            "non_field_errors": ["새 비밀번호는 현재 비밀번호와 달라야 합니다."]
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '인증 실패',
                        value={
                            "detail": "Authentication credentials were not provided."
                        }
                    )
                ]
            )
        },
        tags=['계정 관리']
    )
    def post(self, request):
        """
        현재 비밀번호를 확인하고 새로운 비밀번호로 변경합니다.
        """
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 현재 비밀번호 확인
        current_password = serializer.validated_data['current_password']
        if not request.user.check_password(current_password):
            return Response(
                {"current_password": ["현재 비밀번호가 올바르지 않습니다."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 새 비밀번호로 변경
        new_password = serializer.validated_data['new_password1']
        request.user.set_password(new_password)
        request.user.save()
        
        response_data = {
            'success': True,
            'user_id': request.user.id,
            'message': '비밀번호가 성공적으로 재설정되었습니다.'
        }
        
        response_serializer = PasswordResetResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class EmailCheckView(GenericAPIView):
    """이메일 존재 여부 확인 API"""
    permission_classes = [AllowAny]
    authentication_classes = []  # 인증 없이 사용 가능
    serializer_class = EmailCheckRequestSerializer

    @extend_schema(
        summary="이메일 존재 여부 확인",
        description="입력된 이메일이 시스템에 등록되어 있는지 확인합니다.",
        request=EmailCheckRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=EmailCheckResponseSerializer,
                description='이메일 확인 성공',
                examples=[
                    OpenApiExample(
                        '이메일 존재함',
                        value={
                            "success": True,
                            "email": "user@example.com",
                            "exists": True,
                            "message": "해당 이메일이 등록되어 있습니다."
                        }
                    ),
                    OpenApiExample(
                        '이메일 없음',
                        value={
                            "success": True,
                            "email": "nonexistent@example.com",
                            "exists": False,
                            "message": "해당 이메일이 등록되어 있지 않습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청 데이터',
                examples=[
                    OpenApiExample(
                        '이메일 누락',
                        value={
                            "email": ["이메일을 입력해주세요."]
                        }
                    ),
                    OpenApiExample(
                        '잘못된 이메일 형식',
                        value={
                            "email": ["유효한 이메일 주소를 입력하세요."]
                        }
                    )
                ]
            )
        },
        tags=['계정 관리']
    )
    def post(self, request):
        """
        이메일이 시스템에 등록되어 있는지 확인합니다.
        """
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # 이메일 존재 여부 확인
        email_exists = User.objects.filter(email=email).exists()
        
        if email_exists:
            message = "해당 이메일이 등록되어 있습니다."
        else:
            message = "해당 이메일이 등록되어 있지 않습니다."
        
        response_data = {
            'success': True,
            'email': email,
            'exists': email_exists,
            'message': message
        }
        
        response_serializer = EmailCheckResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class EmailPasswordResetView(GenericAPIView):
    """이메일 기반 비밀번호 재설정 API"""
    permission_classes = [AllowAny]
    authentication_classes = []  # 인증 없이 사용 가능
    serializer_class = EmailPasswordResetRequestSerializer

    @extend_schema(
        summary="이메일 기반 비밀번호 재설정",
        description="이메일과 새 비밀번호를 받아서 해당 계정의 비밀번호를 변경합니다. 인증번호 검증 토큰이 필요합니다. (비밀번호 찾기/재설정용)",
        request=EmailPasswordResetRequestSerializer,
        examples=[
            OpenApiExample(
                '요청 예시',
                value={
                    "email": "user@example.com",
                    "new_password1": "newPassword123!",
                    "new_password2": "newPassword123!",
                    "verification_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(
                response=EmailPasswordResetResponseSerializer,
                description='비밀번호 재설정 성공',
                examples=[
                    OpenApiExample(
                        '비밀번호 재설정 성공',
                        value={
                            "success": True,
                            "email": "user@example.com",
                            "user_id": 1,
                            "message": "비밀번호가 성공적으로 재설정되었습니다."
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='비밀번호 재설정 실패',
                examples=[
                    OpenApiExample(
                        '이메일 없음',
                        value={
                            "email": ["해당 이메일로 등록된 계정이 없습니다."]
                        }
                    ),
                    OpenApiExample(
                        '새 비밀번호 규칙 위반',
                        value={
                            "new_password1": ["비밀번호는 영문을 포함해야 합니다."]
                        }
                    ),
                    OpenApiExample(
                        '새 비밀번호 불일치',
                        value={
                            "non_field_errors": ["새 비밀번호가 일치하지 않습니다."]
                        }
                    ),
                    OpenApiExample(
                        '이메일 형식 오류',
                        value={
                            "email": ["유효한 이메일 주소를 입력하세요."]
                        }
                    ),
                    OpenApiExample(
                        '유효하지 않은 인증 토큰',
                        value={
                            "verification_token": ["유효하지 않은 인증 토큰입니다: Token has expired"]
                        }
                    )
                ]
            )
        },
        tags=['계정 관리']
    )
    def post(self, request):
        """
        이메일과 새 비밀번호를 받아서 해당 계정의 비밀번호를 변경합니다.
        """
        # 요청 데이터 검증 (인증 토큰 검증 포함)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password1']
        verified_phone = serializer.validated_data.get('verified_phone')  # 인증된 전화번호
        
        # 사용자 조회 및 비밀번호 변경
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            response_data = {
                'success': True,
                'email': email,
                'user_id': user.id,
                'message': '비밀번호가 성공적으로 재설정되었습니다.'
            }
            
            response_serializer = EmailPasswordResetResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"email": ["해당 이메일로 등록된 계정이 없습니다."]},
                status=status.HTTP_400_BAD_REQUEST
            )