import requests
import json
import os
from django.conf import settings


class SMSService:
    """
    SMS 발송 서비스
    실제 SMS 발송을 위한 서비스 클래스
    """
    
    def __init__(self):
        # 환경변수에서 SMS 설정 가져오기
        self.api_key = os.getenv('SMS_API_KEY', '')
        self.api_url = os.getenv('SMS_API_URL', '')
        self.sender_number = os.getenv('SMS_SENDER_NUMBER', '')
        self.service_name = os.getenv('SMS_SERVICE_NAME', '다시')
        
        # 개발/운영 환경 구분 (기본값을 development로 설정)
        self.is_development = os.getenv('DJANGO_ENV', 'development') == 'development'
        
        # 디버깅을 위한 로그
        print(f"SMS Service 초기화:")
        print(f"  - DJANGO_ENV: {os.getenv('DJANGO_ENV', 'development')}")
        print(f"  - is_development: {self.is_development}")
        print(f"  - SMS_API_KEY: {'설정됨' if self.api_key else '미설정'}")
        print(f"  - SMS_API_URL: {self.api_url or '미설정'}")
        print(f"  - SERVICEID: {os.getenv('SERVICEID', '미설정')}")
        print(f"  - AWS_ACCESS_KEY_ID: {'설정됨' if os.getenv('AWS_ACCESS_KEY_ID') else '미설정'}")
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
        """운영 환경에서 실제 SMS 발송 (NCP SMS API)"""
        print(f"NCP SMS 발송 시작:")
        
        # NCP SMS API 설정 검증
        service_id = os.getenv('SERVICEID', '')
        access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        
        print(f"  - SERVICEID: {service_id}")
        print(f"  - ACCESS_KEY: {'설정됨' if access_key else '미설정'}")
        print(f"  - SECRET_KEY: {'설정됨' if secret_key else '미설정'}")
        print(f"  - SENDER_NUMBER: {self.sender_number}")
        
        if not all([service_id, access_key, secret_key, self.sender_number]):
            error_msg = 'NCP SMS 서비스 설정이 완료되지 않았습니다. 환경변수를 확인해주세요.'
            print(f"  - 오류: {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'error': 'Missing NCP SMS configuration'
            }
        
        try:
            # NCP SMS API 호출
            import hmac
            import hashlib
            import base64
            import json
            from datetime import datetime
            
            print(f"  - API URL 구성 중...")
            
            # API URL 구성
            api_url = f"https://sens.apigw.ntruss.com/sms/v2/services/{service_id}/messages"
            print(f"  - API URL: {api_url}")
            
            # 타임스탬프
            timestamp = str(int(datetime.now().timestamp() * 1000))
            print(f"  - 타임스탬프: {timestamp}")
            
            # 서명 생성
            method = "POST"
            uri = f"/sms/v2/services/{service_id}/messages"
            message_for_sign = f"{method} {uri}\n{timestamp}\n{access_key}"
            signature = base64.b64encode(
                hmac.new(secret_key.encode(), message_for_sign.encode(), hashlib.sha256).digest()
            ).decode()
            print(f"  - 서명 생성 완료")
            
            # 헤더 설정
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'x-ncp-apigw-timestamp': timestamp,
                'x-ncp-iam-access-key': access_key,
                'x-ncp-apigw-signature-v2': signature
            }
            print(f"  - 헤더 설정 완료")
            
            # 요청 데이터
            data = {
                "type": "SMS",
                "from": self.sender_number,
                "to": [phone_number],
                "content": message
            }
            print(f"  - 요청 데이터: {data}")
            
            print(f"  - API 호출 시작...")
            response = requests.post(api_url, headers=headers, json=data, timeout=10)
            print(f"  - 응답 상태코드: {response.status_code}")
            print(f"  - 응답 내용: {response.text}")
            
            if response.status_code == 202:  # NCP SMS는 202가 성공
                return {
                    'success': True,
                    'message': 'SMS가 성공적으로 발송되었습니다.',
                    'verification_code': verification_code,
                    'phone_number': phone_number,
                    'response': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'SMS 발송 실패: {response.status_code}',
                    'error': response.text,
                    'response_data': response.json() if response.content else None
                }
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"  - NCP SMS API 호출 중 오류 발생:")
            print(f"    오류: {str(e)}")
            print(f"    상세: {error_traceback}")
            
            return {
                'success': False,
                'message': f'NCP SMS API 호출 중 오류가 발생했습니다: {str(e)}',
                'error': str(e),
                'traceback': error_traceback
            }
    
    def _get_current_time(self):
        """현재 시간을 문자열로 반환"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 전역 SMS 서비스 인스턴스
sms_service = SMSService()