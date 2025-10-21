import jwt
import requests
from django.conf import settings
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
        
        # JWK를 RSA 공개키로 변환 (PyJWT 2.0+ 방식)
        try:
            from jwt.algorithms import RSAAlgorithm
            return RSAAlgorithm.from_jwk(json.dumps(key))
        except ImportError:
            # PyJWT 2.0+에서는 다른 방식 사용
            import jwt.algorithms as algorithms
            return algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
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

