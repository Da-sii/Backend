from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import ReviewSerializer
from .models import Review
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
        
        # 프론트에서 받은 새로 업로드할 URL들
        new_urls = request.data.get('urls', [])
        if not new_urls:
            return Response({'error': '업로드할 URL이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # S3 업로더 초기화
        s3_uploader = S3Uploader()
        
        presigned_urls = []
        
        for url in new_urls:
            try:
                # presigned URL 생성 (확장자는 기본값 .jpg 사용)
                presigned_data = s3_uploader.generate_presigned_url(
                    product_id=review.product_id,
                    review_id=review_id
                )
                
                presigned_urls.append({
                    'original_url': url,
                    'upload_url': presigned_data['upload_url'],
                    'final_url': presigned_data['final_url']
                })
                
            except Exception as e:
                return Response({
                    'error': f'Presigned URL 생성 실패: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': f'{len(presigned_urls)}개의 업로드 URL이 생성되었습니다.',
            'presigned_urls': presigned_urls
        }, status=status.HTTP_200_OK)
    