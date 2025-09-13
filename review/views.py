from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .serializers import (
    ReviewSerializer, 
    ReviewListResponseSerializer, 
    ReviewCreateResponseSerializer, 
    ReviewUpdateResponseSerializer,
    ReviewImageUploadRequestSerializer,
    ReviewImageUploadResponseSerializer,
    ReviewImageDeleteResponseSerializer,
    ProductReviewImagesResponseSerializer,
    ProductRatingStatsResponseSerializer,
    ReviewImageDetailResponseSerializer
)
from .models import Review, ReviewImage
from django.shortcuts import get_object_or_404
from .utils import S3Uploader
from django.db.models import Prefetch

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
            201: OpenApiResponse(
                response=ReviewCreateResponseSerializer,
                description='리뷰 작성 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            'message': '리뷰가 성공적으로 작성되었습니다.',
                            'review_id': 1,
                            'user_id': 1,
                            'product_id': 1,
                            'rate': 5,
                            'review': '정말 좋은 제품이었습니다! 향도 좋고 지속력도 길어요. 다음에도 구매하고 싶어요.'
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청 데이터',
                examples=[
                    OpenApiExample(
                        '유효성 검사 실패',
                        value={
                            'rate': ['별점은 1~5 사이여야 합니다.'],
                            'review': ['리뷰는 최소 20자 이상 최대 1000자 이하로 작성해주세요.']
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '인증 실패',
                        value={
                            'detail': 'Authentication credentials were not provided.'
                        }
                    )
                ]
            )
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
        
        # 응답 데이터를 Serializer로 직렬화
        response_data = {
            'message': '리뷰가 성공적으로 작성되었습니다.',
            'review_id': review.id,
            'user_id': request.user.id,
            'product_id': product_id,
            'rate': review.rate,
            'review': review.review
        }
        
        # Serializer로 유효성 검사 (선택사항)
        response_serializer = ReviewCreateResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

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
            200: OpenApiResponse(
                response=ReviewUpdateResponseSerializer,
                description='리뷰 수정 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            'message': '리뷰가 성공적으로 수정되었습니다.',
                            'review_id': 1,
                            'user_id': 1,
                            'product_id': 1,
                            'rate': 4,
                            'review': '품질은 좋지만 가격이 조금 아쉬워요. 그래도 추천합니다.'
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청 데이터',
                examples=[
                    OpenApiExample(
                        '유효성 검사 실패',
                        value={
                            'rate': ['별점은 1~5 사이여야 합니다.'],
                            'review': ['리뷰는 최소 20자 이상 최대 1000자 이하로 작성해주세요.']
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '인증 실패',
                        value={
                            'detail': 'Authentication credentials were not provided.'
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='리뷰를 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '리뷰 없음',
                        value={
                            'detail': 'Not found.'
                        }
                    )
                ]
            )
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
        
        # 응답 데이터를 Serializer로 직렬화
        response_data = {
            'message': '리뷰가 성공적으로 수정되었습니다.',
            'review_id': review.id,
            'user_id': request.user.id,
            'product_id': review.product_id,
            'rate': review.rate,
            'review': review.review
        }
        
        # Serializer로 유효성 검사 (선택사항)
        response_serializer = ReviewUpdateResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewListView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="상품 리뷰 목록 조회",
        description="특정 상품의 모든 리뷰를 조회합니다.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='상품 ID'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ReviewListResponseSerializer,
                description='리뷰 목록 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "reviews": {
                                "닉네임1": {
                                    "rate": 5,
                                    "date": "2024-01-15",
                                    "review": "정말 좋은 제품이었습니다!",
                                    "images": [
                                        {
                                            "url": "https://s3.amazonaws.com/bucket/image1.jpg"
                                        },
                                        {
                                            "url": "https://s3.amazonaws.com/bucket/image2.jpg"
                                        }
                                    ]
                                },
                                "닉네임2": {
                                    "rate": 4,
                                    "date": "2024-01-14",
                                    "review": "품질은 좋지만 가격이 조금 아쉬워요.",
                                    "images": []
                                }
                            }
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='상품을 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '상품 없음',
                        value={
                            "detail": "Not found."
                        }
                    )
                ]
            )
        },
        tags=['리뷰']
    )
    def get(self, request, product_id):
        """
        상품의 모든 리뷰를 조회합니다.
        """
        # 상품 존재 확인
        from products.models import Product
        product = get_object_or_404(Product, id=product_id)
        
        # 리뷰와 이미지를 함께 조회 (N+1 쿼리 방지)
        reviews = Review.objects.filter(product_id=product_id).select_related('user').prefetch_related(
            Prefetch('images', queryset=ReviewImage.objects.all())
        ).order_by('-date')
        
        # Serializer를 사용하여 응답 데이터 구성
        reviews_data = {}
        for review in reviews:
            user_nickname = review.user.nickname
            # ReviewSerializer를 사용하여 리뷰 데이터 직렬화
            review_serializer = ReviewSerializer(review)
            reviews_data[user_nickname] = review_serializer.data
        
        # 최종 응답 데이터 직렬화
        response_data = {
            'success': True,
            'reviews': reviews_data
        }
        
        # Serializer로 유효성 검사 (선택사항)
        response_serializer = ReviewListResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewImageView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewImageUploadRequestSerializer
    
    @extend_schema(
        summary="리뷰 이미지 업로드",
        description="리뷰에 이미지를 업로드합니다. Presigned URL을 생성하여 반환합니다.",
        request=ReviewImageUploadRequestSerializer,
        examples=[
            OpenApiExample(
                '이미지 업로드 요청',
                value={
                    'urls': [
                        'https://example.com/image1.jpg',
                        'https://example.com/image2.jpg'
                    ]
                }
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ReviewImageUploadResponseSerializer,
                description='Presigned URL 생성 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            'message': '2개의 업로드 URL이 생성되었습니다.',
                            'presigned_urls': [
                                {
                                    'image_id': 1,
                                    'original_url': 'https://example.com/image1.jpg',
                                    'upload_url': 'https://s3.amazonaws.com/bucket/...',
                                    'final_url': 'https://s3.amazonaws.com/bucket/...',
                                    'filename': '1/1/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg'
                                },
                                {
                                    'image_id': 2,
                                    'original_url': 'https://example.com/image2.jpg',
                                    'upload_url': 'https://s3.amazonaws.com/bucket/...',
                                    'final_url': 'https://s3.amazonaws.com/bucket/...',
                                    'filename': '1/1/b2c3d4e5-f6g7-8901-bcde-f23456789012.jpg'
                                }
                            ]
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='잘못된 요청 데이터',
                examples=[
                    OpenApiExample(
                        'URL 없음',
                        value={
                            'error': '업로드할 URL이 필요합니다.'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '인증 실패',
                        value={
                            'detail': 'Authentication credentials were not provided.'
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='리뷰를 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '리뷰 없음',
                        value={
                            'detail': 'Not found.'
                        }
                    )
                ]
            ),
            500: OpenApiResponse(
                description='서버 오류',
                examples=[
                    OpenApiExample(
                        'Presigned URL 생성 실패',
                        value={
                            'error': 'Presigned URL 생성 실패: S3 연결 오류'
                        }
                    )
                ]
            )
        },
        tags=['리뷰 이미지']
    )
    def post(self, request, review_id):
        # 리뷰 존재 확인 및 권한 체크
        review = get_object_or_404(Review, id=review_id, user=request.user)
        
        # Serializer로 요청 데이터 유효성 검사
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 유효성 검사된 URL들 가져오기
        original_urls = serializer.validated_data['urls']
        
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
        
        # 응답 데이터를 Serializer로 직렬화
        response_data = {
            'message': f'{len(presigned_urls)}개의 업로드 URL이 생성되었습니다.',
            'presigned_urls': presigned_urls
        }
        
        # Serializer로 유효성 검사 (선택사항)
        response_serializer = ReviewImageUploadResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

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
            200: OpenApiResponse(
                response=ReviewImageDeleteResponseSerializer,
                description='이미지 삭제 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            'message': '이미지가 성공적으로 삭제되었습니다.',
                            'image_id': 1,
                            'filename': '1/1/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='인증되지 않은 사용자',
                examples=[
                    OpenApiExample(
                        '인증 실패',
                        value={
                            'detail': 'Authentication credentials were not provided.'
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='리뷰 또는 이미지를 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '이미지 없음',
                        value={
                            'error': '이미지를 찾을 수 없습니다.'
                        }
                    ),
                    OpenApiExample(
                        '리뷰 없음',
                        value={
                            'detail': 'Not found.'
                        }
                    )
                ]
            )
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
            
            # 응답 데이터를 Serializer로 직렬화
            response_data = {
                'message': '이미지가 성공적으로 삭제되었습니다.',
                'image_id': image_id,
                'filename': filename
            }
            
            # Serializer로 유효성 검사 (선택사항)
            response_serializer = ReviewImageDeleteResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'이미지 삭제 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class ProductReviewImagesView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="상품 리뷰 이미지 URL 목록 조회",
        description="특정 상품의 모든 리뷰 이미지 URL을 조회합니다.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='상품 ID'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ProductReviewImagesResponseSerializer,
                description='상품 리뷰 이미지 URL 목록 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "product_id": 1,
                            "total_images": 3,
                            "image_urls": [
                                "https://s3.amazonaws.com/bucket/image1.jpg",
                                "https://s3.amazonaws.com/bucket/image2.jpg",
                                "https://s3.amazonaws.com/bucket/image3.jpg"
                            ]
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='상품을 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '상품 없음',
                        value={
                            "detail": "Not found."
                        }
                    )
                ]
            )
        },
        tags=['리뷰 이미지']
    )
    def get(self, request, product_id):
        """
        특정 상품의 모든 리뷰 이미지 URL을 조회합니다.
        """
        # 상품 존재 확인
        from products.models import Product
        product = get_object_or_404(Product, id=product_id)
        
        # 1. 해당 상품의 리뷰 ID들 조회
        review_ids = Review.objects.filter(product_id=product_id).values_list('id', flat=True)
        
        # 2. 해당 리뷰 ID들의 이미지 URL들 조회
        image_urls = ReviewImage.objects.filter(
            review_id__in=review_ids
        ).values_list('url', flat=True)
        
        # 3. 응답 데이터 구성
        response_data = {
            'success': True,
            'product_id': product_id,
            'total_images': len(image_urls),
            'image_urls': list(image_urls)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ProductRatingStatsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="상품 별점 통계 조회",
        description="특정 상품의 별점 분포와 평균 별점을 조회합니다.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='상품 ID'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ProductRatingStatsResponseSerializer,
                description='상품 별점 통계 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "product_id": 1,
                            "total_reviews": 15,
                            "average_rating": 4.2,
                            "rating_distribution": {
                                "1": 0,
                                "2": 1,
                                "3": 2,
                                "4": 5,
                                "5": 7
                            }
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='상품을 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '상품 없음',
                        value={
                            "detail": "Not found."
                        }
                    )
                ]
            )
        },
        tags=['리뷰 통계']
    )
    def get(self, request, product_id):
        """
        특정 상품의 별점 통계를 조회합니다.
        """
        # 상품 존재 확인
        from products.models import Product
        product = get_object_or_404(Product, id=product_id)
        
        # 해당 상품의 모든 리뷰 조회
        reviews = Review.objects.filter(product_id=product_id)
        
        # 리뷰가 없는 경우
        if not reviews.exists():
            response_data = {
                'success': True,
                'product_id': product_id,
                'total_reviews': 0,
                'average_rating': 0.0,
                'rating_distribution': {
                    '1': 0,
                    '2': 0,
                    '3': 0,
                    '4': 0,
                    '5': 0
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        # 별점 분포 계산
        rating_counts = {}
        total_rating = 0
        
        for i in range(1, 6):
            count = reviews.filter(rate=i).count()
            rating_counts[str(i)] = count
            total_rating += count * i
        
        # 평균 별점 계산
        total_reviews = reviews.count()
        average_rating = round(total_rating / total_reviews, 1) if total_reviews > 0 else 0.0
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'product_id': product_id,
            'total_reviews': total_reviews,
            'average_rating': average_rating,
            'rating_distribution': rating_counts
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewImageDetailView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="이미지 ID로 리뷰 정보 조회",
        description="특정 이미지 ID에 해당하는 리뷰 정보를 조회합니다.",
        parameters=[
            OpenApiParameter(
                name='image_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='이미지 ID'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ReviewImageDetailResponseSerializer,
                description='리뷰 정보 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "image_id": 1,
                            "review_info": {
                                "url": "https://s3.amazonaws.com/bucket/image1.jpg",
                                "nickname": "닉네임1",
                                "rate": 5,
                                "date": "2024-01-15",
                                "review": "정말 좋은 제품이었습니다! 향도 좋고 지속력도 길어요."
                            }
                        }
                    )
                ]
            ),
            404: OpenApiResponse(
                description='이미지를 찾을 수 없음',
                examples=[
                    OpenApiExample(
                        '이미지 없음',
                        value={
                            "detail": "Not found."
                        }
                    )
                ]
            )
        },
        tags=['리뷰 이미지']
    )
    def get(self, request, image_id):
        """
        특정 이미지 ID에 해당하는 리뷰 정보를 조회합니다.
        """
        # 이미지와 관련 리뷰 정보를 함께 조회 (N+1 쿼리 방지)
        review_image = get_object_or_404(
            ReviewImage.objects.select_related('review', 'review__user'),
            id=image_id
        )
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'image_id': image_id,
            'review_info': {
                'url': review_image.url,
                'nickname': review_image.review.user.nickname,
                'rate': review_image.review.rate,
                'date': review_image.review.date,
                'review': review_image.review.review
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
