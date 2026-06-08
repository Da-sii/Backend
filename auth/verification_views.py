from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse
from django.utils import timezone
import os

from users.models import PhoneVerification
from .serializers import PhoneSendRequestSerializer, PhoneVerifyRequestSerializer
import random
from .verification_service import sms_service
from .utils import parse_phone_number
from .token_utils import generate_verification_token

DAILY_LIMIT = 10
VERIFICATION_TIMEOUT = 300  # 5분 (초)
CACHE_PREFIX = 'phone_verification:'

class PhoneVerificationView(APIView):
    # 전화번호 인증번호 발송 API (SMS)

    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PhoneSendRequestSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'original_phone': {'type': 'string'},
                    'parsed_phone': {'type': 'string'},
                    'message': {'type': 'string'},
                    'remaining_requests': {'type': 'integer'},
                    'sent_at': {'type': 'string'},
                    'verification_code': {'type': 'string'},
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            },
            429: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'remaining_requests': {'type': 'integer'}
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'details': {'type': 'string'}
                }
            }
        },
        tags=['전화번호 인증'],
        summary='전화번호 인증 발송',
        description='전화번호로 인증번호(6자리)를 발송합니다.'
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        
        if not phone_number:
            return Response(
                {'error': '전화번호가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 1. 전화번호 파싱
        parsed_phone = parse_phone_number(phone_number)
        
        if not parsed_phone:
            return Response(
                {'error': '유효하지 않은 전화번호 형식입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 기존 레코드 조회 또는 생성
        obj, created = PhoneVerification.objects.get_or_create(
            phone_number=parsed_phone,
            verification_type=PhoneVerification.VERIFICATION_TYPE_SMS,
            defaults={
                'daily_count' : 0,
                'sent_at' : None,
            }
        )
        
        # 3. 하루 제한 확인
        if obj.is_daily_limit_exceeded():
            return Response(
                {
                    'error': f'하루 최대 {DAILY_LIMIT}회까지만 요청 가능합니다. 내일 다시 시도해주세요.',
                    'remaining_requests': 0
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # 4. 날짜 바뀌었으면 daily_count 리셋
        if obj.sent_at and obj.sent_at.date() < timezone.now().date():
            obj.daily_count = 0
        
        # 5. 인증번호 생성
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # 6. SMS 발송
        sms_result = sms_service.send_verification_sms(parsed_phone, verification_code)
        
        if not sms_result['success']:
            return Response(
                {
                    'error': 'SMS 발송에 실패했습니다.',
                    'details': sms_result['message']
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 7. DB 저장
        obj.verification_code = verification_code
        obj.sent_at = timezone.now()
        obj.daily_count += 1
        obj.save()
        
        return Response({
            'success': True,
            'original_phone': phone_number,
            'parsed_phone': parsed_phone,
            'message': '인증번호가 성공적으로 발송되었습니다.',
            'remaining_requests': DAILY_LIMIT - obj.daily_count,
            'sent_at': obj.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
            'verification_code': verification_code  # 개발용 - 운영에서는 제거
        }, status=status.HTTP_200_OK)

class VerifyCodeView(APIView):
    # 인증번호 검증 후 verification_token 발급 (SMS)

    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PhoneVerifyRequestSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'verification_token': {'type': 'string', 'description': '5분 유효한 인증용 JWT 토큰'},
                    'expires_at': {'type': 'string', 'description': '토큰 만료 시간'},
                    'expires_in_seconds': {'type': 'integer', 'description': '토큰 만료까지 남은 시간(초)'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['전화번호 인증'],
        summary='인증번호 검증',
        description='전화번호와 인증번호를 검증합니다. (유효기간 3분)'
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        verification_code = request.data.get('verification_code')
        
        if not phone_number or not verification_code:
            return Response(
                {'error': '전화번호와 인증번호가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 1. 전화번호 파싱
        parsed_phone = parse_phone_number(phone_number)
        
        if not parsed_phone:
            return Response(
                {'error': '유효하지 않은 전화번호 형식입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. DB에서 레코드 조회
        try:
            obj = PhoneVerification.objects.get(
                phone_number=parsed_phone,
                verification_type=PhoneVerification.VERIFICATION_TYPE_SMS,
            )
        except PhoneVerification.DoesNotExist:
            return Response(
                {'error': '인증번호를 먼저 발송해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. 인증번호 존재 여부 확인
        if not obj.verification_code:
            return Response(
                {'error': '인증번호가 만료되었습니다. 다시 발송해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 4. 만료 확인
        if obj.is_code_expired():
            obj.verification_code = None
            obj.save(update_fields=['verification_code'])
            return Response(
                {'error': '인증번호가 만료되었습니다. (5분 초과)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. 인증번호 검증
        if obj.verification_code != verification_code:
            return Response(
                {'error': '인증번호가 일치하지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 6. 인증 성공 - 인증번호 삭제 + JWT 발급
        obj.delete()

        token_data = generate_verification_token(parsed_phone)

        return Response({
            'success': True,
            'message': '인증번호가 확인되었습니다.',
            'verification_token': token_data['token'],
            'expires_at': token_data['expires_at'],
            'expires_in_seconds': token_data['expires_in_seconds']
        }, status=status.HTTP_200_OK)

class DeleteInfoView(APIView):
    """
    계정 삭제 정보 HTML 페이지를 제공하는 뷰
    구글 배포 규정에 따라 /auth/delete-info/ 경로에서 HTML을 서빙
    """
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    def get(self, request):
        """
        delete_info.html 파일을 읽어서 HTML 응답으로 반환
        """
        try:
            # auth 앱 디렉토리의 절대 경로
            auth_dir = os.path.dirname(os.path.abspath(__file__))
            html_file_path = os.path.join(auth_dir, 'delete_info.html')
            
            # HTML 파일 읽기
            with open(html_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            return HttpResponse(html_content, content_type='text/html; charset=utf-8')
        
        except FileNotFoundError:
            return HttpResponse(
                '<h1>페이지를 찾을 수 없습니다.</h1>', 
                status=404
            )
        except Exception as e:
            return HttpResponse(
                f'<h1>서버 오류가 발생했습니다: {str(e)}</h1>', 
                status=500
            )