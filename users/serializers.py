import re
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from users.models import User

class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="이미 사용 중인 이메일입니다.")]
    )
    password2 = serializers.CharField(write_only=True)
    phoneNumber = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ["id", "email", "password", "password2", "phoneNumber"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate_password(self, data):
        # 비밀번호 규칙 검사(8~20자, 영문/숫자/특수문자 포함)
        if len(data) < 8 or len(data) > 20:
            raise serializers.ValidationError("비밀번호는 8~20자여야 합니다.")
        if not re.search(r"[A-Za-z]", data) or not re.search(r"[0-9]", data) or not re.search(r"[^A-Za-z0-9]", data):
            raise serializers.ValidationError("비밀번호는 영문,숫자,특수문자를 모두 포함해야 합니다.")

        return data

    def validate_phoneNumber(self, data):
        if data:
            if not re.match(r'^01[0-9]-?\d{3,4}-?\d{4}$', data):
                raise serializers.ValidationError("올바른 핸드폰번호 형식이 아닙니다. (예: 010-1234-5678)")
            
            # 중복 검사
            if User.objects.filter(phone_number=data).exists():
                raise serializers.ValidationError("이미 사용 중인 핸드폰번호입니다.")
                
        return data

    def validate(self, data):
        # 비밀번호 확인
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        return data

    def create(self, validated_data):
        validated_data.pop("password2") # DB에는 password2 저장 X
        
        # phoneNumber를 phone_number로 매핑
        if 'phoneNumber' in validated_data:
            validated_data['phone_number'] = validated_data.pop('phoneNumber')

        return User.objects.create_user(**validated_data)

class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data["email"]
        password = data["password"]
        
        # 디버깅을 위한 로그
        print(f"로그인 시도: {email}")
        
        # 사용자 존재 여부 확인
        try:
            user_obj = User.objects.get(email=email)
            print(f"사용자 존재: {user_obj}")
            print(f"사용자 활성화 상태: {user_obj.is_active}")
        except User.DoesNotExist:
            print(f"사용자 없음: {email}")
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        
        # 인증 시도
        user = authenticate(email=email, password=password)
        if not user:
            print(f"인증 실패: {email}")
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        
        print(f"인증 성공: {user}")
        data["user"] = user
        return data

class KakaoLoginSerializer(serializers.Serializer):
    code = serializers.CharField(
        help_text="카카오 로그인 후 받은 authorization code",
        required=True
    )

class KakaoLogoutRequestSerializer(serializers.Serializer):
    """카카오 로그아웃 요청 시리얼라이저"""
    kakao_access_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="카카오에서 발급받은 access_token (선택사항)"
    )

class UserDeleteRequestSerializer(serializers.Serializer):
    """회원탈퇴 요청 시리얼라이저"""
    kakao_access_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="카카오에서 발급받은 access_token (카카오 사용자인 경우 필요)"
    )
    apple_user_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="애플 사용자 ID (애플 사용자인 경우 필요)"
    )

class UserDeleteResponseSerializer(serializers.Serializer):
    """회원탈퇴 응답 시리얼라이저"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_user_id = serializers.IntegerField()
    deleted_email = serializers.EmailField()

class NicknameUpdateRequestSerializer(serializers.Serializer):
    nickname = serializers.CharField(min_length=2, max_length=10)

    def validate_nickname(self, value):
        import re
        # 한글, 영문, 숫자만 허용 (2~10자는 필드에서 이미 검증)
        if not re.fullmatch(r"[A-Za-z0-9가-힣]+", value):
            raise serializers.ValidationError("닉네임은 한글, 영문, 숫자만 사용할 수 있습니다.")

        if User.objects.filter(nickname=value).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
            
        return value


class NicknameUpdateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    user_id = serializers.IntegerField()
    nickname = serializers.CharField()


class PasswordChangeRequestSerializer(serializers.Serializer):
    """비밀번호 변경 요청 시리얼라이저"""
    current_password = serializers.CharField(write_only=True, min_length=1)
    new_password1 = serializers.CharField(write_only=True, min_length=8, max_length=20)
    new_password2 = serializers.CharField(write_only=True, min_length=8, max_length=20)

    def validate_current_password(self, value):
        """현재 비밀번호가 비어있지 않은지 확인"""
        if not value:
            raise serializers.ValidationError("현재 비밀번호를 입력해주세요.")
        return value

    def validate_new_password1(self, value):
        """새 비밀번호 규칙 검증"""
        import re
        if len(value) < 8 or len(value) > 20:
            raise serializers.ValidationError("비밀번호는 8~20자여야 합니다.")
        if not re.search(r"[A-Za-z]", value):
            raise serializers.ValidationError("비밀번호는 영문을 포함해야 합니다.")
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError("비밀번호는 숫자를 포함해야 합니다.")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise serializers.ValidationError("비밀번호는 특수문자를 포함해야 합니다.")
        return value

    def validate(self, data):
        """새 비밀번호 일치 확인"""
        if data["new_password1"] != data["new_password2"]:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        
        # 현재 비밀번호와 새 비밀번호가 같은지 확인
        if data["current_password"] == data["new_password1"]:
            raise serializers.ValidationError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
        
        return data


class PasswordChangeResponseSerializer(serializers.Serializer):
    """비밀번호 변경 응답 시리얼라이저"""
    success = serializers.BooleanField()
    user_id = serializers.IntegerField()
    message = serializers.CharField()


class PhoneNumberFindAccountRequestSerializer(serializers.Serializer):
    """핸드폰번호로 계정 찾기 요청 시리얼라이저"""
    phone_number = serializers.CharField(
        max_length=20,
        help_text="핸드폰번호 (예: 010-1234-5678)"
    )

    def validate_phone_number(self, value):
        """핸드폰번호 형식 검증"""
        import re
        # 한국 핸드폰번호 형식 검증 (010, 011, 016, 017, 018, 019)
        phone_pattern = r'^01[0-9]-?\d{3,4}-?\d{4}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("올바른 핸드폰번호 형식이 아닙니다. (예: 010-1234-5678)")
        return value


class AccountInfoSerializer(serializers.Serializer):
    """계정 정보 시리얼라이저"""
    id = serializers.IntegerField()
    email = serializers.EmailField()
    nickname = serializers.CharField()
    login_type = serializers.CharField()
    created_at = serializers.DateTimeField()


class PhoneNumberFindAccountResponseSerializer(serializers.Serializer):
    """핸드폰번호로 계정 찾기 응답 시리얼라이저"""
    success = serializers.BooleanField()
    accounts = serializers.ListField(
        child=AccountInfoSerializer(),
        help_text="해당 핸드폰번호로 등록된 계정 목록"
    )
    message = serializers.CharField()


class MyPageUserInfoResponseSerializer(serializers.Serializer):
    """마이페이지 사용자 정보 응답 시리얼라이저"""
    success = serializers.BooleanField()
    user_info = serializers.DictField(
        help_text="사용자 정보 (닉네임, 이메일, 로그인 방식, 리뷰 개수)"
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """비밀번호 재설정 요청 시리얼라이저 (계정 찾기용)"""
    current_password = serializers.CharField(
        write_only=True,
        help_text="현재 비밀번호"
    )
    new_password1 = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        help_text="새 비밀번호 (8~20자, 영문/숫자/특수문자 포함)"
    )
    new_password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        help_text="새 비밀번호 확인"
    )

    def validate_current_password(self, value):
        """현재 비밀번호가 비어있지 않은지 확인"""
        if not value or not value.strip():
            raise serializers.ValidationError("현재 비밀번호를 입력해주세요.")
        return value.strip()

    def validate_new_password1(self, value):
        """새 비밀번호 규칙 검증"""
        import re
        if not value or not value.strip():
            raise serializers.ValidationError("새 비밀번호를 입력해주세요.")
        
        value = value.strip()
        if len(value) < 8 or len(value) > 20:
            raise serializers.ValidationError("비밀번호는 8~20자여야 합니다.")
        if not re.search(r"[A-Za-z]", value):
            raise serializers.ValidationError("비밀번호는 영문을 포함해야 합니다.")
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError("비밀번호는 숫자를 포함해야 합니다.")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise serializers.ValidationError("비밀번호는 특수문자를 포함해야 합니다.")
        return value

    def validate(self, data):
        """새 비밀번호 일치 확인 및 현재 비밀번호와 다른지 확인"""
        current_password = data.get("current_password", "").strip()
        new_password1 = data.get("new_password1", "").strip()
        new_password2 = data.get("new_password2", "").strip()
        
        if not new_password2:
            raise serializers.ValidationError("새 비밀번호 확인을 입력해주세요.")
        
        if new_password1 != new_password2:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        
        if current_password == new_password1:
            raise serializers.ValidationError("새 비밀번호는 현재 비밀번호와 달라야 합니다.")
        
        return data


class PasswordResetResponseSerializer(serializers.Serializer):
    """비밀번호 재설정 응답 시리얼라이저"""
    success = serializers.BooleanField()
    user_id = serializers.IntegerField()
    message = serializers.CharField()


class EmailCheckRequestSerializer(serializers.Serializer):
    """이메일 존재 여부 확인 요청 시리얼라이저"""
    email = serializers.EmailField(
        help_text="확인할 이메일 주소"
    )
    
    def validate_email(self, value):
        """이메일 형식 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("이메일을 입력해주세요.")
        return value.strip().lower()


class EmailCheckResponseSerializer(serializers.Serializer):
    """이메일 존재 여부 확인 응답 시리얼라이저"""
    success = serializers.BooleanField()
    email = serializers.EmailField()
    exists = serializers.BooleanField()
    message = serializers.CharField()


class EmailPasswordResetRequestSerializer(serializers.Serializer):
    """이메일 기반 비밀번호 재설정 요청 시리얼라이저"""
    email = serializers.EmailField(
        help_text="비밀번호를 변경할 이메일 주소"
    )
    new_password1 = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        help_text="새 비밀번호 (8~20자, 영문/숫자/특수문자 포함)"
    )
    new_password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        help_text="새 비밀번호 확인"
    )
    verification_token = serializers.CharField(
        write_only=True,
        help_text="인증번호 검증 시 받은 JWT 토큰"
    )

    def validate_email(self, value):
        """이메일 형식 검증 및 존재 여부 확인"""
        if not value or not value.strip():
            raise serializers.ValidationError("이메일을 입력해주세요.")
        
        email = value.strip().lower()
        
        # 이메일이 존재하는지 확인
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError("해당 이메일로 등록된 계정이 없습니다.")
        
        return email

    def validate_new_password1(self, value):
        """새 비밀번호 규칙 검증"""
        import re
        if not value or not value.strip():
            raise serializers.ValidationError("새 비밀번호를 입력해주세요.")
        
        value = value.strip()
        if len(value) < 8 or len(value) > 20:
            raise serializers.ValidationError("비밀번호는 8~20자여야 합니다.")
        if not re.search(r"[A-Za-z]", value):
            raise serializers.ValidationError("비밀번호는 영문을 포함해야 합니다.")
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError("비밀번호는 숫자를 포함해야 합니다.")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise serializers.ValidationError("비밀번호는 특수문자를 포함해야 합니다.")
        return value

    def validate_verification_token(self, value):
        """인증 토큰 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("인증 토큰이 필요합니다.")
        return value.strip()

    def validate(self, data):
        """새 비밀번호 일치 확인 및 인증 토큰 검증"""
        from auth.token_utils import verify_verification_token
        
        new_password1 = data.get("new_password1", "").strip()
        new_password2 = data.get("new_password2", "").strip()
        verification_token = data.get("verification_token", "").strip()
        
        if not new_password2:
            raise serializers.ValidationError("새 비밀번호 확인을 입력해주세요.")
        
        if new_password1 != new_password2:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        
        # 인증 토큰 검증
        token_result = verify_verification_token(verification_token)
        if not token_result['valid']:
            raise serializers.ValidationError({
                "verification_token": [f"유효하지 않은 인증 토큰입니다: {token_result.get('error', '알 수 없는 오류')}"]
            })
        
        # 토큰에서 전화번호 추출하여 저장 (나중에 사용할 수 있도록)
        data['verified_phone'] = token_result.get('phone_number')
        
        return data


class EmailPasswordResetResponseSerializer(serializers.Serializer):
    """이메일 기반 비밀번호 재설정 응답 시리얼라이저"""
    success = serializers.BooleanField()
    email = serializers.EmailField()
    user_id = serializers.IntegerField()
    message = serializers.CharField()


class PhoneNumberAccountInfoRequestSerializer(serializers.Serializer):
    """전화번호로 계정 정보 조회 요청 시리얼라이저"""
    phone_number = serializers.CharField(
        max_length=20,
        help_text="전화번호 (다양한 형식 지원: 010-1234-5678, 01012345678, +82-10-1234-5678 등)"
    )
    
    def validate_phone_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("전화번호가 필요합니다.")
        return value.strip()


class PhoneNumberAccountInfoResponseSerializer(serializers.Serializer):
    """전화번호로 계정 정보 조회 응답 시리얼라이저"""
    success = serializers.BooleanField()
    phone_number = serializers.CharField()
    accounts = serializers.ListField(
        child=serializers.DictField(),
        help_text="해당 전화번호로 가입된 계정들의 리스트"
    )
    message = serializers.CharField()


class AccountInfoSerializer(serializers.Serializer):
    """계정 정보 시리얼라이저"""
    email = serializers.EmailField()
    created_at = serializers.DateTimeField()