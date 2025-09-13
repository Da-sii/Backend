import boto3
import uuid
import os
from django.conf import settings
from botocore.exceptions import ClientError

class S3Uploader:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def generate_presigned_url(self, product_id, review_id):
        """
        S3 presigned URL 생성 (업로드용)
        파일명: productid/reviewid/임의이름
        """
        try:
            # 파일명 생성: productid/reviewid/임의이름 (기본 확장자 .jpg)
            unique_filename = f"{uuid.uuid4()}"
            s3_key = f"{product_id}/{review_id}/{unique_filename}"
            
            # presigned URL 생성 (PUT 요청용)
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ContentType': 'image/jpeg',  # 기본값
                    'ACL': 'public-read'
                },
                ExpiresIn=3600  # 1시간 유효
            )
            
            # 최종 URL 생성
            final_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_key}"
            
            return {
                'upload_url': presigned_url,
                'final_url': final_url
            }
            
        except ClientError as e:
            raise Exception(f"Presigned URL 생성 실패: {str(e)}")
