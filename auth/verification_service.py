import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CoolSMSService:
    """
    쿨 SMS 발송 서비스 (Node.js 코드 참고)
    쿨 SMS Python SDK를 사용한 SMS 발송 서비스 클래스
    """
    
    def __init__(self):
        # 환경변수에서 쿨 SMS 설정 가져오기
        self.api_key = os.getenv('COOL_SMS_API_KEY', '')
        self.api_secret = os.getenv('COOL_SMS_API_SECRET', '')
        self.sender_number = os.getenv('SMS_SENDER_NUMBER', '')
        self.service_name = os.getenv('SMS_SERVICE_NAME', '다시')
        
        # 개발/운영 환경 구분
        self.is_development = os.getenv('DJANGO_ENV', 'development') == 'development'
        
        # 디버깅을 위한 로그
        print(f"쿨 SMS Service 초기화:")
        print(f"  - DJANGO_ENV: {os.getenv('DJANGO_ENV', 'development')}")
        print(f"  - is_development: {self.is_development}")
        print(f"  - COOL_SMS_API_KEY: {'설정됨' if self.api_key else '미설정'}")
        print(f"  - COOL_SMS_API_SECRET: {'설정됨' if self.api_secret else '미설정'}")
        print(f"  - SMS_SENDER_NUMBER: {self.sender_number or '미설정'}")
    
    def send_verification_sms(self, phone_number, verification_code):
        """
        인증번호 SMS 발송
        
        Args:
            phone_number (str): 수신자 전화번호
            verification_code (str): 인증번호
            
        Returns:
            dict: 발송 결과
        """
        try:
            # SMS 메시지 내용
            message = f"[{self.service_name}] 인증번호는 {verification_code}입니다. 3분 내에 입력해주세요."
            
            print(f"SMS 발송 시도:")
            print(f"  - 수신자: {phone_number}")
            print(f"  - 메시지: {message}")
            print(f"  - 개발모드: {self.is_development}")
            
            # 개발 환경에서는 시뮬레이션만 실행
            if self.is_development:
                return self._simulate_sms_sending(phone_number, message, verification_code)
            
            # 운영 환경에서는 실제 SMS 발송
            return self._send_real_sms(phone_number, message, verification_code)
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"SMS 발송 중 오류 발생:")
            print(f"  - 오류: {str(e)}")
            print(f"  - 상세: {error_traceback}")
            
            return {
                'success': False,
                'message': f'SMS 발송 중 오류가 발생했습니다: {str(e)}',
                'error': str(e),
                'traceback': error_traceback
            }
    
    def _simulate_sms_sending(self, phone_number, message, verification_code):
        """개발 환경에서 SMS 발송 시뮬레이션"""
        print(f"SMS 발송 시뮬레이션:")
        print(f"수신자: {phone_number}")
        print(f"메시지: {message}")
        print(f"발송 시간: {self._get_current_time()}")
        
        return {
            'success': True,
            'message': 'SMS가 성공적으로 발송되었습니다. (시뮬레이션)',
            'verification_code': verification_code,
            'phone_number': phone_number
        }
    
    def _send_real_sms(self, phone_number, message, verification_code):
        """운영 환경에서 실제 SMS 발송 (쿨 SMS Python SDK)"""
        print(f"쿨 SMS 발송 시작:")
        
        # 쿨 SMS API 설정 검증
        if not all([self.api_key, self.api_secret, self.sender_number]):
            error_msg = '쿨 SMS 서비스 설정이 완료되지 않았습니다. 환경변수를 확인해주세요.'
            print(f"  - 오류: {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'error': 'Missing Cool SMS configuration'
            }
        
        try:
            # 쿨 SMS Python SDK 사용 (Python 코드 참고)
            from sdk.api.message import Message
            from sdk.exceptions import CoolsmsException
            
            # 쿨 SMS 클라이언트 초기화
            cool = Message(self.api_key, self.api_secret)
            
            # 요청 데이터 (Python 코드와 동일한 구조)
            params = {
                'type': 'sms',  # Message type
                'to': phone_number,  # Recipients Number
                'from': self.sender_number,  # Sender number
                'text': message  # Message
            }
            
            print(f"  - 쿨 SMS 발송 요청:")
            print(f"    to: {phone_number}")
            print(f"    from: {self.sender_number}")
            print(f"    text: {message}")
            
            # SMS 발송
            response = cool.send(params)
            
            print(f"  - 쿨 SMS 발송 완료:")
            print(f"    Success Count: {response.get('success_count', 0)}")
            print(f"    Error Count: {response.get('error_count', 0)}")
            print(f"    Group ID: {response.get('group_id', 'N/A')}")
            
            if "error_list" in response:
                print(f"    Error List: {response['error_list']}")
                return {
                    'success': False,
                    'message': f'SMS 발송 실패: {response["error_list"]}',
                    'error': response['error_list'],
                    'response': response
                }
            
            return {
                'success': True,
                'message': 'SMS가 성공적으로 발송되었습니다.',
                'verification_code': verification_code,
                'phone_number': phone_number,
                'response': response
            }
            
        except CoolsmsException as e:
            print(f"  - 쿨 SMS 오류 발생:")
            print(f"    Error Code: {e.code}")
            print(f"    Error Message: {e.msg}")
            
            return {
                'success': False,
                'message': f'쿨 SMS 오류: {e.msg}',
                'error': f'Code: {e.code}, Message: {e.msg}'
            }
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"  - 쿨 SMS API 호출 중 오류 발생:")
            print(f"    오류: {str(e)}")
            print(f"    상세: {error_traceback}")
            
            return {
                'success': False,
                'message': f'쿨 SMS API 호출 중 오류가 발생했습니다: {str(e)}',
                'error': str(e),
                'traceback': error_traceback
            }
    
    def _get_current_time(self):
        """현재 시간을 문자열로 반환"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 전역 SMS 서비스 인스턴스 (쿨 SMS)
sms_service = CoolSMSService()