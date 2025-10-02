from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from .token_utils import verify_verification_token


class VerificationTokenRequestSerializer(serializers.Serializer):
    """인증 토큰 검증 요청 시리얼라이저"""
    verification_token = serializers.CharField(
        help_text="인증번호 검증 시 받은 JWT 토큰"
    )


class VerificationTokenView(APIView):
    """
    인증 토큰 검증 API
    프론트엔드에서 받은 verification_token을 검증
    """
    permission_classes = [AllowAny]
    serializer_class = VerificationTokenRequestSerializer
    
    @extend_schema(
        summary="인증 토큰 검증",
        description="프론트엔드에서 받은 verification_token을 검증합니다.",
        request=VerificationTokenRequestSerializer,
        responses={
            200: {
                'description': '토큰 검증 성공',
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'phone_number': {'type': 'string'},
                    'expires_at': {'type': 'string'}
                }
            },
            400: {
                'description': '토큰 검증 실패',
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['전화번호 인증']
    )
    def post(self, request):
        """
        인증 토큰을 검증합니다.
        """
        verification_token = request.data.get('verification_token')
        
        if not verification_token:
            return Response(
                {'valid': False, 'error': 'verification_token이 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 토큰 검증
        result = verify_verification_token(verification_token)
        
        if result['valid']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
