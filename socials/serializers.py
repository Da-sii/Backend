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

class AdvertisementInquirySerializer(serializers.Serializer):
    """광고/제휴 문의 시리얼라이저 (DB 저장 없이 이메일 전송만)"""
    
    INQUIRY_TYPE_CHOICES = [
        ('domestic', '국내 광고 문의'),
        ('global', '글로벌 광고 문의'),
        ('other', '기타 문의 (제휴 등)'),
    ]
    
    LAUNCH_STATUS_CHOICES = [
        ('launched', '출시 완료'),
        ('within_1_month', '미출시 (1개월 내 출시 예정)'),
        ('within_3_months', '미출시 (3개월 내 출시 예정)'),
        ('over_3_months', '미출시 (3개월 이상 소요 예정)'),
    ]
    
    # 문의 유형
    inquiry_type = serializers.ChoiceField(
        choices=INQUIRY_TYPE_CHOICES,
        help_text="문의 유형"
    )
    
    # 담당 브랜드명
    brand_name = serializers.CharField(
        max_length=100,
        help_text="담당 브랜드명"
    )
    
    # 브랜드 출시 여부
    launch_status = serializers.ChoiceField(
        choices=LAUNCH_STATUS_CHOICES,
        help_text="브랜드 출시 여부"
    )
    
    # 문의 내용
    inquiry_content = serializers.CharField(
        max_length=1000,
        help_text="문의 내용 (최소 20자, 최대 1000자)"
    )
    
    # 성함
    name = serializers.CharField(
        max_length=50,
        help_text="성함"
    )
    
    # 연락처
    contact_number = serializers.CharField(
        max_length=20,
        help_text="연락처"
    )
    
    # 이메일 주소
    email = serializers.EmailField(
        help_text="이메일 주소"
    )
    
    def validate_inquiry_content(self, value):
        """문의 내용 유효성 검사 (최소 20자, 최대 1000자)"""
        if len(value) < 20:
            raise serializers.ValidationError("문의 내용은 최소 20자 이상 입력해주세요.")
        if len(value) > 1000:
            raise serializers.ValidationError("문의 내용은 최대 1000자까지 입력 가능합니다.")
        return value
    
    def validate_contact_number(self, value):
        """연락처 형식 검사"""
        # 기본적인 한국 전화번호 형식 검사
        import re
        phone_pattern = r'^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$'
        if not re.match(phone_pattern, value.replace('-', '')):
            raise serializers.ValidationError("올바른 연락처 형식을 입력해주세요. (예: 010-1234-5678)")
        return value

class SocialPreLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["apple", "kakao"])
    apple_sub = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    
    def validate(self, data):
        provider = data.get("provider")

        if provider == "apple":
            if not data.get("apple_sub"):
                raise serializers.ValidationError("apple 로그인은 apple_sub이 필요합니다.")

        if provider == "kakao":
            if not data.get("email"):
                raise serializers.ValidationError("kakao 로그인은 email이 필요합니다.")

        return data

        