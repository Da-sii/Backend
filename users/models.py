from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # 비밀번호 해싱
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    nickname = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) # Django가 해싱해서 저장
    kakao = models.BooleanField(default=False)
    google = models.BooleanField(default=False)
    apple = models.BooleanField(default=False)

    # Django 기본 인증 시스템을 위한 필드
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"  # 로그인 ID로 email 사용
    REQUIRED_FIELDS = ["nickname"]  # createsuperuser 시 추가 입력

    def __str__(self):
        return self.email

    class Meta:
        db_table = "users"