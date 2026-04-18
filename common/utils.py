import os
import uuid
import boto3
from django.conf import settings

def upload_banner_to_s3(image) -> str:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    _, ext = os.path.splitext(image.name)
    filename = f"banners/{uuid.uuid4().hex}{ext.lower()}"

    s3.upload_fileobj(
        image,
        settings.AWS_STORAGE_BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": image.content_type},
    )

    return f"{settings.CLOUDFRONT_DOMAIN}/{filename}"