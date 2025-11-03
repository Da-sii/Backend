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
            
            # 개발 환경에서는 시뮬레이션만 실행
            if self.is_development:
                return self._simulate_sms_sending(phone_number, message, verification_code)
            
            # 운영 환경에서는 실제 SMS 발송
            return self._send_real_sms(phone_number, message, verification_code)
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"SMS 발송 중 오류 발생: {str(e)}", exc_info=True)
            
            return {
                'success': False,
                'message': f'SMS 발송 중 오류가 발생했습니다: {str(e)}',
                'error': str(e),
                'traceback': error_traceback
            }
    
    def _simulate_sms_sending(self, phone_number, message, verification_code):
        """개발 환경에서 SMS 발송 시뮬레이션"""
        return {
            'success': True,
            'message': 'SMS가 성공적으로 발송되었습니다. (시뮬레이션)',
            'verification_code': verification_code,
            'phone_number': phone_number
        }
    
    def _send_real_sms(self, phone_number, message, verification_code):
        """운영 환경에서 실제 SMS 발송 (쿨 SMS Python SDK)"""
        # 쿨 SMS API 설정 검증
        if not all([self.api_key, self.api_secret, self.sender_number]):
            error_msg = '쿨 SMS 서비스 설정이 완료되지 않았습니다. 환경변수를 확인해주세요.'
            logger.error(error_msg)
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
            
            # SMS 발송
            response = cool.send(params)
            
            if "error_list" in response:
                logger.error(f"쿨 SMS 발송 실패: {response['error_list']}")
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
            logger.error(f"쿨 SMS 오류 발생: Code {e.code}, Message {e.msg}")
            
            return {
                'success': False,
                'message': f'쿨 SMS 오류: {e.msg}',
                'error': f'Code: {e.code}, Message: {e.msg}'
            }
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"쿨 SMS API 호출 중 오류 발생: {str(e)}", exc_info=True)
            
            return {
                'success': False,
                'message': f'쿨 SMS API 호출 중 오류가 발생했습니다: {str(e)}',
                'error': str(e),
                'traceback': error_traceback
            }


# 전역 SMS 서비스 인스턴스 (쿨 SMS)
sms_service = CoolSMSService()