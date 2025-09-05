from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny] # 인증 필요 없음 (누구나 회원가입 가능)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # serializer 안의 validate_* 메서드들이 실행됨
        user = serializer.save() # User 생성

        # ✅ 여기서 user가 제대로 생성됐는지 확인
        print("DEBUG >>> user.id:", user.id, "user.email:", user.email)

        # 토큰 발급
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        return Response(
            {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
            },
            "access": access,
            "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )