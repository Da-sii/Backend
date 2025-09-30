from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from .serializers import PhoneSendRequestSerializer, PhoneVerifyRequestSerializer
import random
import threading
import time
from datetime import datetime, timedelta
from .verification_service import sms_service
from .utils import parse_phone_number

# 메모리에 저장할 객체
# { phoneNumber: { count: number, lastRequest: Date, verification_code: string, sent_at: Date } }
phone_requests = {}
DAILY_LIMIT = 10

# 하루 단위 초기화 함수
def cleanup_old_requests():
    """하루가 지난 요청 기록을 삭제"""
    current_time = datetime.now()
    phones_to_delete = []
    
    for phone in phone_requests:
        last_request = phone_requests[phone]['lastRequest']
        if current_time - last_request > timedelta(days=1):
            phones_to_delete.append(phone)
    
    for phone in phones_to_delete:
        del phone_requests[phone]
    
    if phones_to_delete:
        print(f"하루 단위 요청 기록 초기화: {len(phones_to_delete)}개 번호 삭제")

# 백그라운드에서 주기적으로 실행되는 정리 함수
def periodic_cleanup():
    """24시간마다 실행되는 정리 함수"""
    while True:
        time.sleep(24 * 60 * 60)  # 24시간 대기
        cleanup_old_requests()

# 백그라운드 스레드 시작
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()


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
        current_time = datetime.now()
        
        # 기존 요청 기록이 있는지 확인
        if parsed_phone in phone_requests:
            request_data = phone_requests[parsed_phone]
            last_request = request_data['lastRequest']
            
            # 하루가 지났으면 카운트 리셋
            if current_time - last_request > timedelta(days=1):
                phone_requests[parsed_phone] = {
                    'count': 1,
                    'lastRequest': current_time,
                    'verification_code': None,
                    'sent_at': None
                }
            else:
                # 하루 내 요청이면 카운트 증가
                request_data['count'] += 1
                request_data['lastRequest'] = current_time
                
                # 하루 제한 초과 확인
                if request_data['count'] > DAILY_LIMIT:
                    return Response(
                        {
                            'error': f'하루 최대 {DAILY_LIMIT}회까지만 요청 가능합니다. 내일 다시 시도해주세요.',
                            'remaining_requests': 0
                        }, 
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
        else:
            # 새로운 전화번호면 초기화
            phone_requests[parsed_phone] = {
                'count': 1,
                'lastRequest': current_time,
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
        
        # 5. 메모리에 인증번호와 발송 시간 저장
        phone_requests[parsed_phone]['verification_code'] = verification_code
        phone_requests[parsed_phone]['sent_at'] = current_time
        
        # 6. 남은 요청 횟수 계산
        remaining_requests = DAILY_LIMIT - phone_requests[parsed_phone]['count']
        
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
                    'verified_phone': {'type': 'string'},
                    'verified_at': {'type': 'string'}
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
        
        # 메모리에서 인증번호 확인
        if parsed_phone not in phone_requests:
            return Response(
                {'error': '인증번호를 먼저 발송해주세요.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stored_data = phone_requests[parsed_phone]
        stored_code = stored_data.get('verification_code')
        sent_at = stored_data.get('sent_at')
        
        if not stored_code:
            return Response(
                {'error': '인증번호가 만료되었습니다. 다시 발송해주세요.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3분(180초) 만료 확인
        current_time = datetime.now()
        if sent_at and (current_time - sent_at).seconds > 180:
            # 만료된 인증번호 삭제
            phone_requests[parsed_phone]['verification_code'] = None
            return Response(
                {'error': '인증번호가 만료되었습니다. (3분 초과)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 인증번호 검증
        if stored_code == verification_code:
            # 인증 성공 시 인증번호 삭제
            phone_requests[parsed_phone]['verification_code'] = None
            return Response({
                'success': True,
                'message': '인증번호가 확인되었습니다.',
                'verified_phone': parsed_phone,
                'verified_at': current_time.strftime('%Y-%m-%d %H:%M:%S')
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': '인증번호가 일치하지 않습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )