import jwt
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
import json
import logging

logger = logging.getLogger(__name__)

APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"

def get_apple_public_key(kid):
    """Apple 공개키를 가져와서 JWT 검증에 사용할 수 있는 형태로 반환"""
    try:
        response = requests.get(APPLE_PUBLIC_KEY_URL)
        response.raise_for_status()
        keys = response.json()["keys"]
        
        # kid가 일치하는 키 찾기
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise ValueError(f"Apple 공개키 조회 실패: kid {kid}를 찾을 수 없습니다")
        
        # JWK를 RSA 공개키로 변환
        try:
            # PyJWT 2.0+ 방식
            from jwt.algorithms import RSAAlgorithm
            return RSAAlgorithm.from_jwk(json.dumps(key))
        except (ImportError, AttributeError):
            try:
                # PyJWT 1.x 방식
                import jwt.algorithms as algorithms
                return algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            except (ImportError, AttributeError):
                # 최신 PyJWT 방식
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                import base64
                
                # JWK에서 RSA 공개키 구성 요소 추출
                n = base64.urlsafe_b64decode(key['n'] + '==')
                e = base64.urlsafe_b64decode(key['e'] + '==')
                
                # RSA 공개키 생성
                public_key = rsa.RSAPublicNumbers(
                    int.from_bytes(e, 'big'),
                    int.from_bytes(n, 'big')
                ).public_key()
                
                return public_key
    except Exception as e:
        raise ValueError(f"Apple 공개키 조회 중 오류 발생: {str(e)}")

def verify_identity_token(identity_token):
    """Apple identity token을 검증하고 payload를 반환"""
    try:
        # 먼저 헤더에서 kid 추출
        unverified_header = jwt.get_unverified_header(identity_token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise ValueError("JWT 헤더에서 kid를 찾을 수 없습니다")
        
        # 개발 환경에서는 디버그 모드 사용
        if settings.DJANGO_ENV == "development":
            logger.info("Apple 토큰 검증 디버그 모드")
            return jwt.decode(
                identity_token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=["HS256", "RS256"],
            )
        
        # 프로덕션 환경에서는 실제 검증
        # Apple 공개키 가져오기
        public_key = get_apple_public_key(kid)
        
        # JWT 토큰 검증
        payload = jwt.decode(
            identity_token,
            public_key,
            audience=settings.APPLE_CLIENT_ID,  # Bundle ID
            issuer="https://appleid.apple.com",
            algorithms=["RS256"],
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise ValueError("토큰이 만료되었습니다")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"유효하지 않은 토큰입니다: {str(e)}")
    except Exception as e:
        raise ValueError(f"토큰 검증 중 오류 발생: {str(e)}")

# 개발용: 검증 없이 payload만 보기 (디버깅용)
def verify_identity_token_debug(identity_token):
    """개발/디버깅용: 서명 검증 없이 payload만 디코딩"""
    return jwt.decode(
        identity_token,
        options={"verify_signature": False, "verify_exp": False},
        algorithms=["HS256", "RS256"],
    )


def send_advertisement_inquiry_email(inquiry_data):
    """광고/제휴 문의 이메일 전송"""
    try:
        from datetime import datetime
        
        # 문의 유형 표시명 매핑
        inquiry_type_display = {
            'domestic': '국내 광고 문의',
            'global': '글로벌 광고 문의',
            'other': '기타 문의 (제휴 등)',
        }
        
        # 출시 여부 표시명 매핑
        launch_status_display = {
            'launched': '출시 완료',
            'within_1_month': '미출시 (1개월 내 출시 예정)',
            'within_3_months': '미출시 (3개월 내 출시 예정)',
            'over_3_months': '미출시 (3개월 이상 소요 예정)',
        }
        
        # 이메일 제목
        subject = f"[다시] 광고/제휴 문의 - {inquiry_data['brand_name']} ({inquiry_type_display[inquiry_data['inquiry_type']]})"
        
        # 현재 시간
        current_time = datetime.now().strftime('%Y년 %m월 %d일 %H:%M')
        
        # 이메일 내용 (HTML)
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    광고/제휴 문의가 접수되었습니다
                </h2>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">문의 정보</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; width: 120px;">문의 유형:</td>
                            <td style="padding: 8px 0;">{inquiry_type_display[inquiry_data['inquiry_type']]}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">브랜드명:</td>
                            <td style="padding: 8px 0;">{inquiry_data['brand_name']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">출시 여부:</td>
                            <td style="padding: 8px 0;">{launch_status_display[inquiry_data['launch_status']]}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">성함:</td>
                            <td style="padding: 8px 0;">{inquiry_data['name']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">연락처:</td>
                            <td style="padding: 8px 0;">{inquiry_data['contact_number']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">이메일:</td>
                            <td style="padding: 8px 0;">{inquiry_data['email']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">접수일시:</td>
                            <td style="padding: 8px 0;">{current_time}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">문의 내용:</td>
                            <td style="padding: 8px 0;">{inquiry_data['inquiry_content']}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 텍스트 버전 (HTML 태그 제거)
        text_content = strip_tags(html_content)
        
        # 발신자 이메일 (설정에서 가져오거나 기본값 사용)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@dasii.kr')
        
        # 수신자 이메일 (관리자 이메일)
        recipient_list = [getattr(settings, 'ADMIN_EMAIL', 'admin@dasii.kr')]
        
        # 이메일 전송
        send_mail(
            subject=subject,
            message=text_content,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"광고/제휴 문의 이메일 전송 완료 - 브랜드: {inquiry_data['brand_name']}")
        return True
        
    except Exception as e:
        logger.error(f"광고/제휴 문의 이메일 전송 실패 - 브랜드: {inquiry_data.get('brand_name', 'Unknown')}, 오류: {str(e)}")
        return False

