from rest_framework import serializers

from users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        # 비밀번호 확인
        if data['password'] != data['password2']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        # 비밀번호 규칙 검사(8~20자, 영문/숫자/특수문자 포함)
        import re
        password = data['password']
        if len(password) < 8 or len(password) > 20:
            raise serializers.ValidationError("비밀번호는 8~20자여야 합니다.")
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[^A-Za-z0-9]', password):
            raise serializers.ValidationError("비밀번호는 영문,숫자,특수문자를 모두 포함해야 합니다.")

        return data

    def create(self, validated_data):
        validated_data.pop('password2') # DB에는 password2 저장 X
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            nickname=validated_data.get('nickname',""),
        )
        return user