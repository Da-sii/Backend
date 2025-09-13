from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ReviewSerializer
from .models import Review, ReviewImage
from django.shortcuts import get_object_or_404
from .utils import S3Uploader

class PostView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer
    
    def post(self, request, product_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 리뷰 생성
        review = Review.objects.create(
            user=request.user,
            product_id=product_id,
            rate=serializer.validated_data['rate'],
            review=serializer.validated_data['review']
        )
        
        return Response({
            'message': '리뷰가 성공적으로 작성되었습니다.',
            'review_id': review.id,
            'user_id': request.user.id,
            'product_id': product_id,
            'rate': review.rate,
            'review': review.review
        }, status=status.HTTP_201_CREATED)

class ReviewUpdateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer
    
    def patch(self, request, review_id):
        # 리뷰 존재 확인 및 권한 체크 (본인 리뷰만 수정 가능)
        review = get_object_or_404(Review, id=review_id, user=request.user)
        
        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # 리뷰 수정
        serializer.save()
        
        return Response({
            'message': '리뷰가 성공적으로 수정되었습니다.',
            'review_id': review.id,
            'user_id': request.user.id,
            'product_id': review.product_id,
            'rate': review.rate,
            'review': review.review
        }, status=status.HTTP_200_OK)

class ReviewImageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, review_id):
        # 리뷰 존재 확인 및 권한 체크
        review = get_object_or_404(Review, id=review_id, user=request.user)
        
        # 프론트에서 받은 원본 URL들
        original_urls = request.data.get('urls', [])
        if not original_urls:
            return Response({'error': '업로드할 URL이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # S3 업로더 초기화
        s3_uploader = S3Uploader()
        
        presigned_urls = []
        created_images = []
        
        for original_url in original_urls:
            try:
                # 원본 파일명에서 확장자 추출
                import os
                file_extension = os.path.splitext(original_url)[1] or '.jpg'
                
                # presigned URL 생성 (백엔드에서 파일명 생성)
                presigned_data = s3_uploader.generate_presigned_url(
                    product_id=review.product_id,
                    review_id=review_id,
                    file_extension=file_extension
                )
                
                # ReviewImage 객체 생성 (DB에 저장) - 파일명만 저장
                review_image = ReviewImage.objects.create(
                    review=review,
                    url=presigned_data['filename']
                )
                created_images.append(review_image)
                
                presigned_urls.append({
                    'image_id': review_image.id,
                    'original_url': original_url,
                    'upload_url': presigned_data['upload_url'],
                    'final_url': presigned_data['final_url'],
                    'filename': presigned_data['filename']  # DB에 저장된 파일명
                })
                
            except Exception as e:
                # 실패한 경우 생성된 이미지들 삭제
                for img in created_images:
                    img.delete()
                return Response({
                    'error': f'Presigned URL 생성 실패: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': f'{len(presigned_urls)}개의 업로드 URL이 생성되었습니다.',
            'presigned_urls': presigned_urls
        }, status=status.HTTP_200_OK)
    