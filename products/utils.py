import boto3, uuid, os
from typing import List
from django.utils import timezone
from django.db.models import F, TextField, Value
from django.db.models.functions import Replace
from django.conf import settings
from products.models import Product, ProductDailyView, ProductImage

def record_view(product: Product):
    # 누적 증가
    Product.objects.filter(id=product.id).update(viewCount=F("viewCount") + 1)

    today = timezone.now().date()
    daily_view, created = ProductDailyView.objects.get_or_create(
        product=product, date=today
    )
    daily_view.views = F("views") + 1
    daily_view.save()

def remove_spaces(field: str) -> Replace:
    """DB 필드 값에서 공백을 제거하는 표현식 (띄어쓰기 무시 검색용)"""
    return Replace(field, Value(" "), Value(""), output_field=TextField())

def normalize_keyword(keyword: str) -> str:
    """검색어에서 모든 공백(탭, 연속 공백 포함)을 제거"""
    return "".join(keyword.split())

def upload_images_to_s3(product: Product, images: List) -> List[ProductImage]:
    """
    제품 이미지를 S3에 업로드하고 ProductImage 객체 리스트를 반환
    
    Args:
        product: 이미지가 속할 제품 객체
        images: 업로드할 이미지 파일 리스트
        
    Returns:
        ProductImage 객체 리스트
    """
    if not images:
        return []
    
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )
    
    uploaded_images = []
    for img in images:
        # 확장자만 추출 (안전)
        _, ext = os.path.splitext(img.name)
        ext = ext.lower()

        # 완전히 안전한 파일명
        filename = f"products/{uuid.uuid4().hex}{ext}"

        s3.upload_fileobj(
            img,
            settings.AWS_STORAGE_BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": img.content_type},
        )
        url = f"{settings.CLOUDFRONT_DOMAIN}/{filename}"
        uploaded_images.append(ProductImage(product=product, url=url))
    
    return uploaded_images
