from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timedelta
import jwt
from django.conf import settings


def generate_verification_token(phone_number: str) -> dict:
    """
    인증번호 검증 성공 시 5분 유효한 JWT 토큰 생성
    """
    # 5분 후 만료 시간
    exp_time = datetime.utcnow() + timedelta(minutes=5)
    
    # 토큰 페이로드
    payload = {
        'phone_number': phone_number,
        'token_type': 'phone_verification',
        'exp': exp_time,
        'iat': datetime.utcnow(),
        'purpose': 'phone_verification'
    }
    
    # JWT 토큰 생성 (Django SECRET_KEY 사용)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    return {
        'token': token,
        'expires_at': exp_time.strftime('%Y-%m-%d %H:%M:%S'),
        'expires_in_seconds': 300  # 5분
    }


def verify_verification_token(token: str) -> dict:
    """
    인증용 JWT 토큰 검증
    """
    try:
        # 토큰 디코딩
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        # 토큰 타입 확인
        if payload.get('token_type') != 'phone_verification':
            return {'valid': False, 'error': 'Invalid token type'}
        
        # 목적 확인
        if payload.get('purpose') != 'phone_verification':
            return {'valid': False, 'error': 'Invalid token purpose'}
        
        return {
            'valid': True,
            'phone_number': payload.get('phone_number'),
            'expires_at': datetime.fromtimestamp(payload.get('exp')).strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except Exception as e:
        return {'valid': False, 'error': f'Token verification failed: {str(e)}'}
