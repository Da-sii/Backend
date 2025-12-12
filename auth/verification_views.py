from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse
from django.core.cache import cache
from django.utils import timezone
import os
from .serializers import PhoneSendRequestSerializer, PhoneVerifyRequestSerializer
import random
from datetime import datetime, timedelta
from .verification_service import sms_service
from .utils import parse_phone_number
from .token_utils import generate_verification_token

DAILY_LIMIT = 10
VERIFICATION_TIMEOUT = 180  # 3분 (초)
CACHE_PREFIX = 'phone_verification:'


class PhoneVerificationView(APIView):
    """
    전화번호 인증 통합 API
    전화번호 파싱 + 제한 확인 + 인증번호 발송을 하나의 API로 통합
    """
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
        """
        전화번호를 받아서 파싱하고 인증번호를 발송하는 통합 API
        """
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
        
        # 2. 하루 제한 확인
        current_time = timezone.now()
        cache_key = f"{CACHE_PREFIX}{parsed_phone}"
        
        # 캐시에서 기존 요청 기록 확인 (에러 발생 시 새로 시작)
        try:
            request_data = cache.get(cache_key)
        except Exception:
            # 캐시 테이블이 없거나 다른 에러 발생 시 새로 시작
            request_data = None
        
        if request_data:
            last_request_str = request_data.get('lastRequest')
            if last_request_str:
                try:
                    # datetime 문자열을 datetime 객체로 변환
                    if isinstance(last_request_str, str):
                        # ISO 형식 파싱 시도
                        try:
                            last_request = datetime.fromisoformat(last_request_str.replace('Z', '+00:00'))
                        except ValueError:
                            # 다른 형식 시도 (문자열 형식이 다를 수 있음)
                            last_request = datetime.fromisoformat(last_request_str)
                        
                        # naive datetime을 timezone-aware로 변환
                        if last_request.tzinfo is None:
                            last_request = timezone.make_aware(last_request)
                    else:
                        last_request = last_request_str
                    
                    # 하루가 지났으면 카운트 리셋
                    if current_time - last_request > timedelta(days=1):
                        request_data = {
                            'count': 1,
                            'lastRequest': current_time.isoformat(),
                            'verification_code': None,
                            'sent_at': None
                        }
                    else:
                        # 하루 내 요청이면 카운트 증가
                        request_data['count'] = request_data.get('count', 0) + 1
                        request_data['lastRequest'] = current_time.isoformat()
                        
                        # 하루 제한 초과 확인
                        if request_data['count'] > DAILY_LIMIT:
                            return Response(
                                {
                                    'error': f'하루 최대 {DAILY_LIMIT}회까지만 요청 가능합니다. 내일 다시 시도해주세요.',
                                    'remaining_requests': 0
                                }, 
                                status=status.HTTP_429_TOO_MANY_REQUESTS
                            )
                except Exception:
                    # 파싱 에러 발생 시 새로 시작
                    request_data = {
                        'count': 1,
                        'lastRequest': current_time.isoformat(),
                        'verification_code': None,
                        'sent_at': None
                    }
        else:
            # 새로운 전화번호면 초기화
            request_data = {
                'count': 1,
                'lastRequest': current_time.isoformat(),
                'verification_code': None,
                'sent_at': None
            }
        
        # 3. 인증번호 생성
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # 4. SMS 발송
        sms_result = sms_service.send_verification_sms(parsed_phone, verification_code)
        
        if not sms_result['success']:
            return Response(
                {
                    'error': 'SMS 발송에 실패했습니다.',
                    'details': sms_result['message']
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 5. 캐시에 인증번호와 발송 시간 저장 (24시간 유지)
        request_data['verification_code'] = verification_code
        request_data['sent_at'] = current_time.isoformat()
        try:
            cache.set(cache_key, request_data, timeout=24 * 60 * 60)  # 24시간 캐시
        except Exception as e:
            # 캐시 저장 실패 시 에러 반환
            return Response(
                {
                    'error': '인증번호 저장에 실패했습니다. 잠시 후 다시 시도해주세요.',
                    'details': str(e) if str(e) else '알 수 없는 오류'
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 6. 남은 요청 횟수 계산
        remaining_requests = DAILY_LIMIT - request_data['count']
        
        return Response({
            'success': True,
            'original_phone': phone_number,
            'parsed_phone': parsed_phone,
            'message': '인증번호가 성공적으로 발송되었습니다.',
            'remaining_requests': remaining_requests,
            'sent_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'verification_code': verification_code  # 개발용 - 실제 운영에서는 제거
        }, status=status.HTTP_200_OK)

class VerifyCodeView(APIView):
    """
    인증번호 검증 API
    전화번호와 인증번호를 받아서 검증
    """
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
        """
        인증번호 검증
        """
        phone_number = request.data.get('phone_number')
        verification_code = request.data.get('verification_code')
        
        if not phone_number or not verification_code:
            return Response(
                {'error': '전화번호와 인증번호가 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 전화번호 파싱
        parsed_phone = parse_phone_number(phone_number)
        
        if not parsed_phone:
            return Response(
                {'error': '유효하지 않은 전화번호 형식입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 캐시에서 인증번호 확인
        cache_key = f"{CACHE_PREFIX}{parsed_phone}"
        try:
            stored_data = cache.get(cache_key)
        except Exception:
            return Response(
                {'error': '인증번호 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if not stored_data:
            return Response(
                {'error': '인증번호를 먼저 발송해주세요.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stored_code = stored_data.get('verification_code')
        sent_at_str = stored_data.get('sent_at')
        
        if not stored_code:
            return Response(
                {'error': '인증번호가 만료되었습니다. 다시 발송해주세요.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3분(180초) 만료 확인
        current_time = timezone.now()
        if sent_at_str:
            try:
                # datetime 문자열을 datetime 객체로 변환
                if isinstance(sent_at_str, str):
                    try:
                        sent_at = datetime.fromisoformat(sent_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        sent_at = datetime.fromisoformat(sent_at_str)
                    # naive datetime을 timezone-aware로 변환
                    if sent_at.tzinfo is None:
                        sent_at = timezone.make_aware(sent_at)
                else:
                    sent_at = sent_at_str
                
                time_diff = current_time - sent_at
                if time_diff.total_seconds() > VERIFICATION_TIMEOUT:
                    # 만료된 인증번호 삭제
                    stored_data['verification_code'] = None
                    try:
                        cache.set(cache_key, stored_data, timeout=24 * 60 * 60)
                    except Exception:
                        pass  # 캐시 저장 실패해도 에러는 반환하지 않음
                    return Response(
                        {'error': '인증번호가 만료되었습니다. (3분 초과)'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception:
                # 시간 파싱 에러 시 만료 처리하지 않음 (다른 검증으로 넘어감)
                pass
        
        # 인증번호 검증
        if stored_code == verification_code:
            # 인증 성공 시 인증번호 삭제
            stored_data['verification_code'] = None
            try:
                cache.set(cache_key, stored_data, timeout=24 * 60 * 60)
            except Exception:
                pass  # 캐시 저장 실패해도 성공 처리
            
            # 5분 유효한 JWT 토큰 생성
            token_data = generate_verification_token(parsed_phone)
            
            return Response({
                'success': True,
                'message': '인증번호가 확인되었습니다.',
                'verification_token': token_data['token'],
                'expires_at': token_data['expires_at'],
                'expires_in_seconds': token_data['expires_in_seconds']
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': '인증번호가 일치하지 않습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class DeleteInfoView(APIView):
    """
    계정 삭제 정보 HTML 페이지를 제공하는 뷰
    구글 배포 규정에 따라 /auth/delete-info/ 경로에서 HTML을 서빙
    """
    permission_classes = [AllowAny]
    
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