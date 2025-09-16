from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import re


def get_user_id_from_request(request):

    # 1. Authorization 헤더 가져오기
    authorization_header = request.META.get("HTTP_AUTHORIZATION")
    
    if not authorization_header:
        raise ValueError("Authorization 헤더가 필요합니다. Bearer <access_token> 형태로 헤더를 포함해주세요.")
    
    # 2. Bearer 토큰에서 access_token 추출
    try:
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise ValueError("Authorization 헤더 형식이 올바르지 않습니다. 'Bearer <token>' 형태여야 합니다.")
        access_token = parts[1]
    except (IndexError, AttributeError) as e:
        raise ValueError(f"Authorization 헤더 파싱 중 오류가 발생했습니다: {str(e)}")
    
    # 3. JWT 토큰에서 user_id 추출
    try:
        token = AccessToken(access_token)
        user_id = token["user_id"]
        return user_id
    except (InvalidToken, TokenError, KeyError) as e:
        raise InvalidToken(f"유효하지 않은 토큰입니다: {str(e)}")


def parse_phone_number(phone_number):
    """
    전화번호를 파싱하여 표준 형식으로 변환
    
    Args:
        phone_number (str): 파싱할 전화번호
        
    Returns:
        str: 표준 형식의 전화번호 (예: 010-1234-5678) 또는 None
    """
    if not phone_number:
        return None
        
    # 숫자만 추출
    digits_only = re.sub(r'[^\d]', '', phone_number)
    
    # 한국 전화번호 패턴 검증 및 파싱
    if digits_only.startswith('010'):
        if len(digits_only) == 11:
            return f"010-{digits_only[3:7]}-{digits_only[7:]}"
    elif digits_only.startswith('02'):
        if len(digits_only) == 9 or len(digits_only) == 10:
            if len(digits_only) == 9:
                return f"02-{digits_only[2:5]}-{digits_only[5:]}"
            else:
                return f"02-{digits_only[2:6]}-{digits_only[6:]}"
    elif digits_only.startswith(('031', '032', '033', '041', '042', '043', '044', '051', '052', '053', '054', '055', '061', '062', '063', '064')):
        if len(digits_only) == 10 or len(digits_only) == 11:
            if len(digits_only) == 10:
                return f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
            else:
                return f"{digits_only[:3]}-{digits_only[3:7]}-{digits_only[7:]}"
    
    return None
