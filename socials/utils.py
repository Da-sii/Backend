import jwt

APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"

# 개발용: 검증 없이 payload만 보기
def verify_identity_token(token):
    return jwt.decode(
        token,
        options={"verify_signature": False, "verify_exp": False},
        algorithms=["HS256", "RS256"],
    )

# 배포용: 실제 Apple 공개키 검증
# def get_apple_public_key(kid):
#     response = requests.get(APPLE_PUBLIC_KEY_URL)
#     keys = response.json()["keys"]
#     key = next((k for k in keys if k["kid"] == kid), None)
#     if not key:
#         raise ValueError("Apple 공개키 조회 실패")
#     return RSAAlgorithm.from_jwk(key)
#
# def verify_apple_token(identity_token):
#     header = jwt.get_unverified_header(identity_token)
#     public_key = get_apple_public_key(header["kid"])
#     payload = jwt.decode(
#         identity_token,
#         public_key,
#         audience="com.your.bundle.id",  # Apple client_id로 교체
#         issuer="https://appleid.apple.com",
#         algorithms=["RS256"],
#     )
#     return payload
