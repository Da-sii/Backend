from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .serializers import ReviewSerializer
from .models import Review, ReviewImage
from django.shortcuts import get_object_or_404
from .utils import S3Uploader

@method_decorator(csrf_exempt, name='dispatch')
class PostView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer
    
    @extend_schema(
        summary="리뷰 작성",
        description="상품에 대한 리뷰를 작성합니다.",
        request=ReviewSerializer,
        examples=[
            OpenApiExample(
                '리뷰 작성 요청',
                value={
                    'rate': 5,
                    'review': '정말 좋은 제품이었습니다! 향도 좋고 지속력도 길어요. 다음에도 구매하고 싶어요.'
                }
            )
        ],
        responses={
            201: {
                'description': '리뷰 작성 성공',
                'examples': {
                    'application/json': {
                        'message': '리뷰가 성공적으로 작성되었습니다.',
                        'review_id': 1,
                        'user_id': 1,
                        'product_id': 1,
                        'rate': 5,
                        'review': '정말 좋은 제품이었습니다! 향도 좋고 지속력도 길어요. 다음에도 구매하고 싶어요.'
                    }
                }
            },
            400: {
                'description': '잘못된 요청 데이터',
                'examples': {
                    'application/json': {
                        'rate': ['별점은 1~5 사이여야 합니다.'],
                        'review': ['리뷰는 최소 20자 이상 최대 1000자 이하로 작성해주세요.']
                    }
                }
            },
            401: {'description': '인증되지 않은 사용자'}
        },
        tags=['리뷰']
    )
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

@method_decorator(csrf_exempt, name='dispatch')
class ReviewUpdateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer
    
    @extend_schema(
        summary="리뷰 수정",
        description="작성한 리뷰를 수정합니다.",
        request=ReviewSerializer,
        examples=[
            OpenApiExample(
                '리뷰 수정 요청',
                value={
                    'rate': 4,
                    'review': '품질은 좋지만 가격이 조금 아쉬워요. 그래도 추천합니다.'
                }
            )
        ],
        responses={
            200: {
                'description': '리뷰 수정 성공',
                'examples': {
                    'application/json': {
                        'message': '리뷰가 성공적으로 수정되었습니다.',
                        'review_id': 1,
                        'user_id': 1,
                        'product_id': 1,
                        'rate': 4,
                        'review': '품질은 좋지만 가격이 조금 아쉬워요. 그래도 추천합니다.'
                    }
                }
            },
            400: {
                'description': '잘못된 요청 데이터',
                'examples': {
                    'application/json': {
                        'rate': ['별점은 1~5 사이여야 합니다.'],
                        'review': ['리뷰는 최소 20자 이상 최대 1000자 이하로 작성해주세요.']
                    }
                }
            },
            401: {'description': '인증되지 않은 사용자'},
            404: {'description': '리뷰를 찾을 수 없음'}
        },
        tags=['리뷰']
    )
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

@method_decorator(csrf_exempt, name='dispatch')
class ReviewImageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="리뷰 이미지 업로드",
        description="리뷰에 이미지를 업로드합니다. Presigned URL을 생성하여 반환합니다.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'urls': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': '업로드할 이미지 URL 목록'
                    }
                },
                'required': ['urls']
            }
        },
        responses={
            200: {
                'description': 'Presigned URL 생성 성공',
                'examples': {
                    'application/json': {
                        'message': '2개의 업로드 URL이 생성되었습니다.',
                        'presigned_urls': [
                            {
                                'image_id': 1,
                                'original_url': 'https://example.com/image1.jpg',
                                'upload_url': 'https://s3.amazonaws.com/...',
                                'final_url': 'https://s3.amazonaws.com/...',
                                'filename': '1/1/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg'
                            }
                        ]
                    }
                }
            },
            400: {
                'description': '잘못된 요청 데이터',
                'examples': {
                    'application/json': {
                        'error': '업로드할 URL이 필요합니다.'
                    }
                }
            },
            401: {'description': '인증되지 않은 사용자'},
            404: {'description': '리뷰를 찾을 수 없음'}
        },
        tags=['리뷰 이미지']
    )
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

@method_decorator(csrf_exempt, name='dispatch')
class ReviewImageDeleteView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="리뷰 이미지 삭제",
        description="리뷰에서 특정 이미지를 삭제합니다. S3에서 파일도 함께 삭제됩니다.",
        parameters=[
            OpenApiParameter(
                name='review_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='리뷰 ID'
            ),
            OpenApiParameter(
                name='image_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='삭제할 이미지 ID'
            )
        ],
        responses={
            200: {
                'description': '이미지 삭제 성공',
                'examples': {
                    'application/json': {
                        'message': '이미지가 성공적으로 삭제되었습니다.',
                        'image_id': 1,
                        'filename': '1/1/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg'
                    }
                }
            },
            401: {'description': '인증되지 않은 사용자'},
            404: {
                'description': '리뷰 또는 이미지를 찾을 수 없음',
                'examples': {
                    'application/json': {
                        'error': '이미지를 찾을 수 없습니다.'
                    }
                }
            }
        },
        tags=['리뷰 이미지']
    )
    def delete(self, request, review_id, image_id):
        """
        리뷰 이미지 삭제 (경로 파라미터로 image_id 받음)
        """
        # 리뷰 존재 확인 및 권한 체크
        review = get_object_or_404(Review, id=review_id, user=request.user)
        
        # 삭제할 이미지 조회
        image_to_delete = get_object_or_404(ReviewImage, id=image_id, review=review)
        
        try:
            # S3에서 파일 삭제
            s3_uploader = S3Uploader()
            s3_uploader.s3_client.delete_object(
                Bucket=s3_uploader.bucket_name,
                Key=image_to_delete.url  # DB에 저장된 파일명
            )
            
            # DB에서 레코드 삭제
            filename = image_to_delete.url
            image_to_delete.delete()
            
            return Response({
                'message': '이미지가 성공적으로 삭제되었습니다.',
                'image_id': image_id,
                'filename': filename
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'이미지 삭제 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
