import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model, login
from django.conf import settings

User = get_user_model()

@csrf_exempt
def kakao_token_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        body = json.loads(request.body)
        code = body.get("code")
    except Exception:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if not code:
        return JsonResponse({"error": "Missing authorization code"}, status=400)

    # 1) 토큰 발급
    token_response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
            "client_secret": settings.KAKAO_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=5,
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    if not access_token:
        return JsonResponse(
            {"error": "Failed to get access token", "detail": token_json}, status=400
        )

    # 2) 사용자 정보
    profile_response = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=5,
    )
    profile_json = profile_response.json()
    print(json.dumps(profile_json, indent=2, ensure_ascii=False))  # 디버깅용

    kakao_id = profile_json.get("id")
    kakao_account = profile_json.get("kakao_account", {})  # ← 먼저 할당
    profile = kakao_account.get("profile", {})             # 보조 포인터
    email = kakao_account.get("email")
    nickname = profile.get("nickname", "")

    if not kakao_id:
        return JsonResponse({"error": "Missing kakao_id"}, status=400)

    # 이메일 기반 가입/로그인 정책: email이 없으면 400으로 안내
    if not email:
        return JsonResponse({
            "error": "Email consent required",
            "detail": {
                "message": "카카오 동의항목에서 이메일을 선택(또는 필수)로 설정하고, 기존 연결을 해제한 뒤 다시 로그인해야 합니다.",
                "tips": [
                    "개발자 콘솔 > 카카오 로그인 > 동의항목에서 '카카오계정(이메일)' 활성화",
                    "테스트 계정을 '팀원'으로 추가 후 재로그인",
                    "기존 연결 해제(https://developers.kakao.com/tool/unlink) 후 다시 시도"
                ]
            }
        }, status=400)

    # 3) 이메일로 사용자 조회/갱신
    try:
        user = User.objects.get(email=email)
        if not user.kakao:
            user.kakao = True
            user.save(update_fields=["kakao"])
        created = False
    except User.DoesNotExist:
        # 비밀번호는 건드리지 않는 정책 → set_unusable_password 사용 안 함
        user = User.objects.create_user(
            email=email,
            nickname=nickname or f"kakao_{kakao_id}",
            kakao=True,
        )
        created = True

    # 4) 세션 로그인
    login(request, user)

    return JsonResponse({
        "message": "Login successful" if not created else "User created and logged in",
        "user": {
            "id": user.id,
            "nickname": user.nickname,
            "email": user.email,
            "kakao": user.kakao,
        }
    })
