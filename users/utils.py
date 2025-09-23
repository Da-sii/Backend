from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def generate_jwt_tokens_with_metadata(user, token_type):
    """
    사용자에 대한 JWT 토큰을 생성하고 메타데이터를 추가합니다.
    
    Args:
        user: User 객체
        token_type: 로그인 타입 ('email', 'kakao', 'apple')
    
    Returns:
        dict: access와 refresh 토큰을 포함한 딕셔너리
    """
    refresh = RefreshToken.for_user(user)
    
    # JWT 토큰에 메타데이터 추가 (refresh와 access 토큰 모두에)
    refresh['tokenType'] = token_type
    refresh.access_token['tokenType'] = token_type
    
    access = str(refresh.access_token)
    refresh_token = str(refresh)
    
    return {
        'access': access,
        'refresh': refresh_token
    }


def get_token_type_from_token(token_string):
    """
    JWT 토큰에서 tokenType 메타데이터를 추출합니다.
    
    Args:
        token_string: JWT 토큰 문자열 (access token 또는 refresh token)
    
    Returns:
        str: tokenType ('email', 'kakao', 'apple') 또는 None
    """
    try:
        # 먼저 AccessToken으로 시도
        try:
            token = AccessToken(token_string)
            return token.get('tokenType')
        except InvalidToken:
            # AccessToken이 실패하면 RefreshToken으로 시도
            token = RefreshToken(token_string)
            return token.get('tokenType')
    except InvalidToken:
        return None
