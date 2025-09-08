from rest_framework import serializers

class AppleSigninSerializer(serializers.Serializer):
    identityToken = serializers.CharField(help_text="Apple에서 발급받은 identityToken")