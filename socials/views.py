import json
import requests
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from drf_spectacular.utils import extend_schema

from users.models import User
from socials.serializers import AppleSigninSerializer
from socials.utils import verify_identity_token

# Create your views here.
class AppleSigninView(GenericAPIView):
    serializer_class = AppleSigninSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identityToken = serializer.validated_data['identityToken']
        
        try:
            payload = verify_identity_token(identityToken)
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"토큰 검증 실패: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        appleId = payload['sub']
        email = payload.get('email', f'{appleId}@apple.com')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "apple": True,
                "nickname": User.objects.generate_nickname(),
            },
        )

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
            status=status.HTTP_200_OK,
        )
