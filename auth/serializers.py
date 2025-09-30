from rest_framework import serializers


class PhoneSendRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(help_text="전화번호 (예: 01012345678 또는 010-1234-5678)")


class PhoneVerifyRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(help_text="전화번호 (예: 01012345678 또는 010-1234-5678)")
    verification_code = serializers.CharField(max_length=6, help_text="6자리 인증번호")