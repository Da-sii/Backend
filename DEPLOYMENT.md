# 배포 환경 설정 가이드

## 1. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

## 2. 환경 변수 설정

`.env` 파일에 다음 환경 변수들을 설정해야 합니다:

### 데이터베이스
- `DB_NAME`: PostgreSQL 데이터베이스 이름
- `DB_USER`: PostgreSQL 사용자 이름
- `DB_PASSWORD`: PostgreSQL 비밀번호
- `DB_HOST`: PostgreSQL 호스트
- `DB_PORT`: PostgreSQL 포트

### AWS 설정
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키
- `AWS_STORAGE_BUCKET_NAME`: S3 버킷 이름
- `AWS_S3_REGION_NAME`: S3 리전
- `AWS_S3_BASE_URL`: S3 베이스 URL
- `CLOUDFRONT_DOMAIN`: CloudFront 도메인

### SMS 서비스 (쿨 SMS)
- `COOL_SMS_API_KEY`: 쿨 SMS API 키
- `COOL_SMS_API_SECRET`: 쿨 SMS API 시크릿
- `SMS_SENDER_NUMBER`: 발신 번호
- `SMS_SERVICE_NAME`: 서비스 이름

### 기타
- `DJANGO_ENV`: `production` 또는 `development`
- `KAKAO_REST_API_KEY`: 카카오 REST API 키
- `KAKAO_REDIRECT_URI`: 카카오 리다이렉트 URI
- `KAKAO_CLIENT_SECRET`: 카카오 클라이언트 시크릿

## 3. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

## 4. 캐시 테이블 생성 (필수!)

인증번호 기능을 위해 **반드시** 실행해야 합니다:

```bash
python manage.py createcachetable
```

이 명령은 `django_cache` 테이블을 생성합니다.

## 5. 정적 파일 수집 (필요한 경우)

```bash
python manage.py collectstatic --noinput
```

## 6. 서버 실행

### 개발 환경
```bash
python manage.py runserver
```

### 프로덕션 환경 (Gunicorn 사용 예시)
```bash
gunicorn dasii_backend.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## 중요 사항

⚠️ **캐시 테이블이 없으면 인증번호 기능이 작동하지 않습니다!**

배포 후 500 에러가 발생하면 다음을 확인하세요:
1. `django_cache` 테이블이 생성되었는지 확인
2. 데이터베이스 연결이 정상인지 확인
3. 환경 변수가 올바르게 설정되었는지 확인

