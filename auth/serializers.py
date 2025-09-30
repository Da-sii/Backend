from rest_framework import serializers


class PhoneVerificationRequestSerializer(serializers.Serializer):
    """전화번호 인증 요청 시리얼라이저"""
    phone_number = serializers.CharField(
        max_length=20,
        help_text="전화번호 (다양한 형식 지원: 010-1234-5678, 01012345678, +82-10-1234-5678 등)",
        example="010-2308-6047"
    )
    verification_code = serializers.CharField(
        max_length=6,
        allow_blank=True,
        required=False,
        default="",
        help_text="인증번호 (발송 시에는 빈 문자열)",
        example=""
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
        help_text="전화번호 (다양한 형식 지원: 010-1234-5678, 01012345678, +82-10-1234-5678 등)",
        example="010-2308-6047"
    )
    verification_code = serializers.CharField(
        max_length=6,
        help_text="6자리 인증번호",
        example="123456"
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


class ErrorResponseSerializer(serializers.Serializer):
    """에러 응답 시리얼라이저"""
    error = serializers.CharField()
