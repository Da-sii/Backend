from rest_framework import serializers

class AppleSigninSerializer(serializers.Serializer):
    identityToken = serializers.CharField(
        help_text="Apple에서 발급받은 identityToken",
        max_length=2000,
        error_messages={
            'required': 'identityToken은 필수입니다.',
            'blank': 'identityToken은 비어있을 수 없습니다.',
            'invalid': '유효하지 않은 identityToken 형식입니다.'
        }
    )
    
    def validate_identityToken(self, value):
        """identityToken 기본 유효성 검사"""
        if not value or not value.strip():
            raise serializers.ValidationError("identityToken은 비어있을 수 없습니다.")
        
        # JWT 토큰은 보통 3개의 부분(header.payload.signature)으로 구성
        parts = value.split('.')
        if len(parts) != 3:
            raise serializers.ValidationError("유효하지 않은 JWT 토큰 형식입니다.")
        
        return value