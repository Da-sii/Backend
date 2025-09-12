from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def get_user_id_from_request(request):

    # 1. Authorization 헤더 가져오기
    authorization_header = request.META.get('HTTP_AUTHORIZATION')
    
    if not authorization_header:
        raise ValueError("Authorization 헤더가 필요합니다. Bearer <access_token> 형태로 헤더를 포함해주세요.")
    
    # 2. Bearer 토큰에서 access_token 추출
    try:
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise ValueError("Authorization 헤더 형식이 올바르지 않습니다. 'Bearer <token>' 형태여야 합니다.")
        access_token = parts[1]
    except (IndexError, AttributeError) as e:
        raise ValueError(f"Authorization 헤더 파싱 중 오류가 발생했습니다: {str(e)}")
    
    # 3. JWT 토큰에서 user_id 추출
    try:
        token = AccessToken(access_token)
        user_id = token['user_id']
        return user_id
    except (InvalidToken, TokenError, KeyError) as e:
        raise InvalidToken(f"유효하지 않은 토큰입니다: {str(e)}")
