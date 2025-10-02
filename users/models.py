from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import random
import string

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, nickname=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)

        if not nickname:
            nickname = self.generate_nickname()

        user = self.model(email=email, nickname=nickname, **extra_fields)
        user.set_password(password)  # 비밀번호 해싱
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

    @staticmethod
    def generate_nickname():
        while True:
            number = "".join(random.choices(string.digits, k=6))
            nickname = f"user{number}"
            if not User.objects.filter(nickname=nickname).exists():
                return nickname

class User(AbstractBaseUser, PermissionsMixin):
    nickname = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) # Django가 해싱해서 저장
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    kakao = models.BooleanField(default=False)
    google = models.BooleanField(default=False)
    apple = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # 가입일 추가
    # Django 기본 인증 시스템을 위한 필드
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"  # 로그인 ID로 email 사용
    REQUIRED_FIELDS = []  # createsuperuser 시 이메일/비번만 묻도록 변경

    def __str__(self):
        return self.email

    class Meta:
        db_table = "users"