from rest_framework import serializers

class PhoneVerificationRequestSerializer(serializers.Serializer):
    """전화번호 인증 요청 시리얼라이저"""
    phone_number = serializers.CharField(
        max_length=20,
        help_text="전화번호 (다양한 형식 지원: 010-1234-5678, 01012345678, +82-10-1234-5678 등)"
    )
    verification_code = serializers.CharField(
        max_length=6,
        allow_blank=True,
        required=False,
        default="",
        help_text="인증번호 (발송 시에는 빈 문자열)"
    )
    
    def validate_phone_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("전화번호가 필요합니다.")
        return value.strip()

class PhoneVerificationResponseSerializer(serializers.Serializer):
    """전화번호 인증 응답 시리얼라이저"""
    success = serializers.BooleanField()
    message = serializers.CharField()

class VerifyCodeRequestSerializer(serializers.Serializer):
    """인증번호 검증 요청 시리얼라이저"""
    phone_number = serializers.CharField(
        max_length=20,
        help_text="전화번호 (다양한 형식 지원: 010-1234-5678, 01012345678, +82-10-1234-5678 등)"
    )
    verification_code = serializers.CharField(
        max_length=6,
        help_text="6자리 인증번호"
    )
    
    def validate_phone_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("전화번호가 필요합니다.")
        return value.strip()
    
    def validate_verification_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("인증번호가 필요합니다.")
        if len(value.strip()) != 6 or not value.strip().isdigit():
            raise serializers.ValidationError("인증번호는 6자리 숫자여야 합니다.")
        return value.strip()

class VerifyCodeResponseSerializer(serializers.Serializer):
    """인증번호 검증 응답 시리얼라이저"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    verification_token = serializers.CharField(help_text="5분 유효한 인증용 JWT 토큰")
    expires_at = serializers.CharField(help_text="토큰 만료 시간")
    expires_in_seconds = serializers.IntegerField(help_text="토큰 만료까지 남은 시간(초)")

class ErrorResponseSerializer(serializers.Serializer):
    """에러 응답 시리얼라이저"""
    error = serializers.CharField()

class PhoneSendRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(help_text="전화번호 (예: 01012345678 또는 010-1234-5678)")

class PhoneVerifyRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(help_text="전화번호 (예: 01012345678 또는 010-1234-5678)")
    verification_code = serializers.CharField(max_length=6, help_text="6자리 인증번호")