from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="이미 사용 중인 이메일입니다.")]
    )
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    # def validate_email(self, data):
    #     if User.objects.filter(email=data).exists():
    #         raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
    #
    #     return data

    def validate_password(self, data):
        # 비밀번호 규칙 검사(8~20자, 영문/숫자/특수문자 포함)
        import re
        if len(data) < 8 or len(data) > 20:
            raise serializers.ValidationError("비밀번호는 8~20자여야 합니다.")
        if not re.search(r'[A-Za-z]', data) or not re.search(r'[0-9]', data) or not re.search(r'[^A-Za-z0-9]', data):
            raise serializers.ValidationError("비밀번호는 영문,숫자,특수문자를 모두 포함해야 합니다.")

        return data

    def validate(self, data):
        # 비밀번호 확인
        if data['password'] != data['password2']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        return data

    def create(self, validated_data):
        validated_data.pop('password2') # DB에는 password2 저장 X

        return User.objects.create_user(**validated_data)