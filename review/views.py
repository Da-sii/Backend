from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from products.models import ProductImage
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
    ReviewImageDetailResponseSerializer,
    UserReviewsResponseSerializer,
    ReviewDeleteResponseSerializer,
    ReviewReportRequestSerializer,
    ReviewReportResponseSerializer,
    ReviewDetailResponseSerializer,
    UserReviewCheckResponseSerializer
)
from .models import Review, ReviewImage, ReviewReport, ReviewReportReason
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
        
        # 리뷰 수정 (updated 필드를 True로 설정)
        updated_review = serializer.save(updated=True)
        
        # 응답 데이터를 Serializer로 직렬화
        response_data = {
            'message': '리뷰가 성공적으로 수정되었습니다.',
            'review_id': updated_review.id,
            'user_id': request.user.id,
            'product_id': updated_review.product_id,
            'rate': updated_review.rate,
            'review': updated_review.review
        }
        
        # Serializer로 유효성 검사 (선택사항)
        response_serializer = ReviewUpdateResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewListView(GenericAPIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="상품 리뷰 페이지네이션 조회",
        description="특정 상품의 리뷰를 페이지네이션으로 조회합니다. 특정 리뷰 ID부터 21개씩 반환하며, 해당 ID가 없으면 가장 가까운 리뷰부터 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='상품 ID'
            ),
            OpenApiParameter(
                name='review_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='시작할 리뷰 ID (해당 ID가 없으면 가장 가까운 리뷰부터 반환)'
            ),
            OpenApiParameter(
                name='sort',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='정렬 방식 (high: 별점 높은 순, low: 별점 낮은 순, time: 최신순)',
                required=False,
                enum=['high', 'low', 'time']
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
    def get(self, request, product_id, review_id):
        """
        상품의 리뷰를 페이지네이션으로 조회합니다.
        특정 review_id부터 21개씩 반환하며, 해당 ID가 없으면 가장 가까운 리뷰부터 반환합니다.
        """
        # 상품 존재 확인 및 이미지 prefetch
        from products.models import Product
        product = get_object_or_404(
            Product.objects.prefetch_related('images'), 
            id=product_id
        )
        
        # 정렬 방식 결정
        sort_param = request.GET.get('sort', 'time')
        if sort_param == 'high':
            order_by = ['-rate', 'id']  # 별점 높은 순, ID 오름차순
        elif sort_param == 'low':
            order_by = ['rate', 'id']   # 별점 낮은 순, ID 오름차순
        else:  # time 또는 기본값
            order_by = ['-date', '-id']  # 최신순, ID 내림차순
        
        # 리뷰 쿼리셋 생성 (정렬 방식에 따라)
        reviews_query = Review.objects.filter(product_id=product_id).select_related('user').prefetch_related(
            Prefetch('images', queryset=ReviewImage.objects.all())
        ).order_by(*order_by)
        
        # review_id가 0이면 처음 요청으로 판단
        if review_id == 0:
            # 처음부터 21개 조회
            reviews = list(reviews_query[:21])
        else:
            # 정렬된 쿼리셋을 리스트로 변환
            all_reviews = list(reviews_query)
            
            # 특정 review_id의 위치 찾기
            target_index = None
            for i, review in enumerate(all_reviews):
                if review.id == review_id:
                    target_index = i
                    break
            
            if target_index is not None:
                # 해당 review_id 다음부터 21개 조회 (해당 ID 포함하지 않음)
                reviews = all_reviews[target_index + 1:target_index + 22]
            else:
                # 해당 review_id가 없으면, review_id보다 큰 리뷰 중 가장 작은 ID를 가진 리뷰 찾기
                closest_index = None
                for i, review in enumerate(all_reviews):
                    if review.id > review_id:
                        closest_index = i
                        break
                
                if closest_index is not None:
                    reviews = all_reviews[closest_index:closest_index + 21]
                else:
                    # review_id보다 큰 리뷰가 없으면 빈 배열 반환
                    reviews = []
        
        # 리뷰가 없는 경우 처리
        if not reviews:
            response_data = {
                'success': True,
                'product_id': product_id,
                'product_info': {
                    'id': product.id,
                    'name': product.name,
                    'company': product.company,
                    'image': product.images.first().url if product.images.exists() else ''
                },
                'reviews': []
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        # Serializer를 사용하여 응답 데이터 구성
        reviews_data = []
        for review in reviews:
            # ReviewSerializer를 사용하여 리뷰 데이터 직렬화
            review_serializer = ReviewSerializer(review)
            review_data = review_serializer.data
            review_data['user_nickname'] = review.user.nickname
            reviews_data.append(review_data)
        
        # 제품 정보 구성 (첫 번째 이미지 가져오기 - 이미 prefetch됨)
        first_image = product.images.first()
        product_info = {
            'id': product.id,
            'name': product.name,
            'company': product.company,
            'image': first_image.url if first_image else ''
        }
        
        # 최종 응답 데이터 구성
        response_data = {
            'success': True,
            'product_id': product_id,
            'product_info': product_info,
            'reviews': reviews_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

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
                # 파일명에서 확장자 추출
                import os
                
                # 파일명에서 확장자 추출 (URL이든 파일명이든 상관없이)
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
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="상품 리뷰 이미지 URL 목록 조회 (페이지네이션)",
        description="특정 상품의 리뷰 이미지 URL을 페이지네이션으로 조회합니다. image_id가 0이면 최신순으로 21개, 그 외에는 해당 ID 다음으로 21개 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='상품 ID'
            ),
            OpenApiParameter(
                name='image_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='시작할 이미지 ID (0이면 최신순으로 21개, 그 외에는 해당 ID 다음으로 21개)'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ProductReviewImagesResponseSerializer,
                description='상품 리뷰 이미지 URL 목록 조회 성공',
                examples=[
                    OpenApiExample(
                        '첫 페이지 (image_id=0)',
                        value={
                            "success": True,
                            "product_id": 1,
                            "total_images": 50,
                            "current_page_images": 21,
                            "image_urls": [
                                {"id": 32, "url": "1/5/3ad48f95-aa89-4327-a78f-1953464fae8f.png"},
                                {"id": 31, "url": "1/5/2bc37e84-9a78-3216-a67e-0842353e9d7e.jpg"},
                                {"id": 30, "url": "1/5/1ab26d73-8a67-2105-a56d-9731242d8c6d.jpg"}
                            ]
                        }
                    ),
                    OpenApiExample(
                        '다음 페이지 (image_id=15)',
                        value={
                            "success": True,
                            "product_id": 1,
                            "total_images": 50,
                            "current_page_images": 21,
                            "image_urls": [
                                {"id": 14, "url": "1/5/0ab15c62-7a56-1094-a45c-8620131c7b5c.jpg"},
                                {"id": 13, "url": "1/5/9ab04b51-6a45-0983-a34b-7519020b6a4b.jpg"},
                                {"id": 12, "url": "1/5/8ab03a40-5a34-0872-a23a-6408919a593a.jpg"}
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
    def get(self, request, product_id, image_id):
        """
        특정 상품의 리뷰 이미지 URL을 페이지네이션으로 조회합니다.
        image_id가 0이면 최신순으로 21개, 그 외에는 해당 ID 다음으로 21개 반환합니다.
        """
        # 상품 존재 확인
        from products.models import Product
        product = get_object_or_404(Product, id=product_id)
        
        # 1. 해당 상품의 리뷰 ID들 조회
        review_ids = Review.objects.filter(product_id=product_id).values_list('id', flat=True)
        
        # 2. 해당 리뷰 ID들의 이미지들을 ID 내림차순으로 조회 (최신순)
        images_query = ReviewImage.objects.filter(
            review_id__in=review_ids
        ).order_by('-id')
        
        # 3. 페이지네이션 로직
        if image_id == 0:
            # 첫 페이지: 최신순으로 21개
            images = list(images_query[:21])
        else:
            # 해당 ID 다음으로 21개
            images = list(images_query.filter(id__lt=image_id)[:21])
        
        # 4. 이미지 데이터 구성 (ID와 URL 포함)
        image_data = [{'id': image.id, 'url': image.url} for image in images]
        
        # 5. 전체 이미지 개수 조회
        total_images = images_query.count()
        
        # 6. 응답 데이터 구성
        response_data = {
            'success': True,
            'product_id': product_id,
            'total_images': total_images,
            'current_page_images': len(image_data),
            'image_urls': image_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewDetailView(GenericAPIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="리뷰 상세 조회",
        description="특정 리뷰 ID에 대한 상세 정보를 조회합니다. 리뷰 작성자 정보, 상품 정보, 별점, 내용, 이미지 등을 포함합니다.",
        parameters=[
            OpenApiParameter(
                name='review_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='조회할 리뷰 ID'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ReviewDetailResponseSerializer,
                description='리뷰 상세 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "review": {
                                "id": 1,
                                "user": {
                                    "id": 3,
                                    "nickname": "이상현",
                                    "email": "s-h-lee@naver.com"
                                },
                                "product": {
                                    "id": 1,
                                    "name": "향수 제품명",
                                    "company": "회사명",
                                    "price": 50000,
                                    "unit": "ml",
                                    "piece": 1,
                                    "productType": "향수",
                                    "viewCount": 150
                                },
                                "rate": 5,
                                "review": "정말 좋은 제품이었습니다! 향도 좋고 지속력도 길어요.",
                                "date": "2024-01-15",
                                "updated": False,
                                "images": [
                                    {
                                        "id": 1,
                                        "url": "1/1/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg"
                                    },
                                    {
                                        "id": 2,
                                        "url": "1/1/b2c3d4e5-f6g7-8901-bcde-f23456789012.jpg"
                                    }
                                ]
                            }
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
                            "detail": "Not found."
                        }
                    )
                ]
            )
        },
        tags=['리뷰 상세']
    )
    def get(self, request, review_id):
        """
        특정 리뷰의 상세 정보를 조회합니다.
        """
        # 리뷰 존재 확인 및 관련 데이터 prefetch
        review = get_object_or_404(
            Review.objects.select_related('user', 'product').prefetch_related(
                'images'
            ),
            id=review_id
        )
        
        # 사용자 정보
        user_info = {
            'id': review.user.id,
            'nickname': review.user.nickname,
            'email': review.user.email
        }
        
        # 상품 정보
        product_info = {
            'id': review.product.id,
            'name': review.product.name,
            'company': review.product.company,
            'price': review.product.price,
            'unit': review.product.unit,
            'piece': review.product.piece,
            'productType': review.product.productType,
            'viewCount': review.product.viewCount
        }
        
        # 이미지 정보
        images_info = [
            {
                'id': image.id,
                'url': image.url
            }
            for image in review.images.all()
        ]
        
        # 리뷰 상세 정보 구성
        review_data = {
            'id': review.id,
            'user': user_info,
            'product': product_info,
            'rate': review.rate,
            'review': review.review,
            'date': review.date,
            'updated': review.updated,
            'images': images_info
        }
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'review': review_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ProductRatingStatsView(GenericAPIView):
    permission_classes = [AllowAny]
    
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
    permission_classes = [AllowAny]
    
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

@method_decorator(csrf_exempt, name='dispatch')
class UserReviewsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="사용자 리뷰 페이지네이션 조회",
        description="현재 로그인한 사용자의 리뷰를 페이지네이션으로 조회합니다. 특정 review_id부터 21개씩 반환하며, 해당 ID가 없으면 가장 가까운 리뷰부터 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='review_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='시작할 리뷰 ID (해당 ID가 없으면 가장 가까운 리뷰부터 반환)'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=UserReviewsResponseSerializer,
                description='사용자 리뷰 목록 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "user_id": 1,
                            "total_reviews": 3,
                            "reviews": [
                                {
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
                                {
                                    "rate": 4,
                                    "date": "2024-01-14",
                                    "review": "품질은 좋지만 가격이 조금 아쉬워요.",
                                    "images": []
                                },
                                {
                                    "rate": 5,
                                    "date": "2024-01-13",
                                    "review": "다음에도 구매하고 싶어요!",
                                    "images": [
                                        {
                                            "url": "https://s3.amazonaws.com/bucket/image3.jpg"
                                        }
                                    ]
                                }
                            ]
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
                            "detail": "Authentication credentials were not provided."
                        }
                    )
                ]
            )
        },
        tags=['사용자 리뷰']
    )
    def get(self, request, review_id):
        """
        현재 로그인한 사용자의 리뷰를 페이지네이션으로 조회합니다.
        특정 review_id부터 21개씩 반환하며, 해당 ID가 없으면 가장 가까운 리뷰부터 반환합니다.
        """
        # 현재 사용자의 리뷰 쿼리셋 생성 (최신순으로 정렬)
        reviews_query = Review.objects.filter(
            user=request.user
        ).select_related('product').prefetch_related(
            Prefetch('images', queryset=ReviewImage.objects.all()),
            Prefetch('product__images', queryset=ProductImage.objects.all())
        ).order_by('-date', '-id')
        
        # review_id가 0이면 처음 요청으로 판단
        if review_id == 0:
            # 처음부터 21개 조회
            reviews = list(reviews_query[:21])
        else:
            # 정렬된 쿼리셋을 리스트로 변환
            all_reviews = list(reviews_query)
            
            # 특정 review_id의 위치 찾기
            target_index = None
            for i, review in enumerate(all_reviews):
                if review.id == review_id:
                    target_index = i
                    break
            
            if target_index is not None:
                # 해당 review_id 다음부터 21개 조회 (해당 ID 포함하지 않음)
                reviews = all_reviews[target_index + 1:target_index + 22]
            else:
                # 해당 review_id가 없으면, review_id보다 큰 리뷰 중 가장 작은 ID를 가진 리뷰 찾기
                closest_index = None
                for i, review in enumerate(all_reviews):
                    if review.id > review_id:
                        closest_index = i
                        break
                
                if closest_index is not None:
                    reviews = all_reviews[closest_index:closest_index + 21]
                else:
                    # review_id보다 큰 리뷰가 없으면 빈 배열 반환
                    reviews = []
        
        # 마이페이지용 Serializer를 사용하여 리뷰 데이터 직렬화
        from .serializers import MyPageReviewSerializer
        reviews_serializer = MyPageReviewSerializer(reviews, many=True)
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'user_id': request.user.id,
            'reviews': reviews_serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewDeleteView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="리뷰 삭제",
        description="작성한 리뷰를 삭제합니다. 본인이 작성한 리뷰만 삭제 가능합니다.",
        parameters=[
            OpenApiParameter(
                name='review_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='삭제할 리뷰 ID'
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ReviewDeleteResponseSerializer,
                description='리뷰 삭제 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "message": "리뷰가 성공적으로 삭제되었습니다.",
                            "review_id": 1,
                            "user_id": 1,
                            "product_id": 1
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
                            "detail": "Authentication credentials were not provided."
                        }
                    )
                ]
            ),
            403: OpenApiResponse(
                description='권한 없음 (본인 리뷰가 아님)',
                examples=[
                    OpenApiExample(
                        '권한 없음',
                        value={
                            "detail": "You do not have permission to perform this action."
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
                            "detail": "Not found."
                        }
                    )
                ]
            )
        },
        tags=['리뷰']
    )
    def delete(self, request, review_id):
        """
        리뷰를 삭제합니다. 본인이 작성한 리뷰만 삭제 가능합니다.
        """
        # 리뷰 존재 확인 및 권한 체크 (본인 리뷰만 삭제 가능)
        review = get_object_or_404(Review, id=review_id, user=request.user)
        
        # 리뷰 정보 저장 (삭제 전에)
        review_id_value = review.id
        user_id_value = review.user.id
        product_id_value = review.product_id
        
        # 리뷰 삭제
        review.delete()
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'message': '리뷰가 성공적으로 삭제되었습니다.',
            'review_id': review_id_value,
            'user_id': user_id_value,
            'product_id': product_id_value
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    

@method_decorator(csrf_exempt, name='dispatch')
class ReviewReportView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewReportRequestSerializer

    @extend_schema(
        summary="리뷰 신고",
        description="특정 리뷰를 신고합니다. 동일 사용자는 같은 리뷰를 한 번만 신고할 수 있습니다.",
        request=ReviewReportRequestSerializer,
        responses={
            201: OpenApiResponse(response=ReviewReportResponseSerializer, description='신고 생성 성공'),
            400: OpenApiResponse(description='유효성 오류 또는 중복 신고'),
            401: OpenApiResponse(description='인증 필요'),
            404: OpenApiResponse(description='리뷰 없음')
        },
        tags=['리뷰 신고']
    )
    def post(self, request, review_id):
        review = get_object_or_404(Review, id=review_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']

        # 중복 신고 방지 - 데이터베이스 제약조건을 활용한 안전한 처리
        from django.db import IntegrityError
        
        # 먼저 중복 검사 (성능 최적화)
        if ReviewReport.objects.filter(review=review, reporter=request.user).exists():
            return Response({
                'success': False,
                'message': '이미 신고한 리뷰입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 데이터베이스 레벨에서 중복 방지
        try:
            report = ReviewReport.objects.create(
                review=review,
                reporter=request.user,
                reason=reason,
            )
        except IntegrityError:
            # 동시성 문제로 인한 중복 발생 시 처리
            return Response({
                'success': False,
                'message': '이미 신고한 리뷰입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': '신고 처리 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_data = {
            'success': True,
            'message': '신고가 접수되었습니다.',
            'report_id': report.id,
            'review_id': review.id,
            'reporter_id': request.user.id,
            'reason': report.reason,
            'created_at': report.created_at,
        }

        response_serializer = ReviewReportResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

@method_decorator(csrf_exempt, name='dispatch')
class UserReviewCheckView(GenericAPIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="사용자 리뷰 작성 여부 확인",
        description="현재 사용자가 특정 제품에 리뷰를 작성했는지 확인합니다.",
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
                response=UserReviewCheckResponseSerializer,
                description='리뷰 작성 여부 확인 성공',
                examples=[
                    OpenApiExample(
                        '리뷰 작성함',
                        value={
                            "success": True,
                            "product_id": 1,
                            "user_id": 1,
                            "has_review": True,
                            "review_id": 5
                        }
                    ),
                    OpenApiExample(
                        '리뷰 작성 안함',
                        value={
                            "success": True,
                            "product_id": 1,
                            "user_id": 1,
                            "has_review": False,
                            "review_id": None
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
        tags=['리뷰 확인']
    )
    def get(self, request, product_id):
        """
        현재 사용자가 특정 제품에 리뷰를 작성했는지 확인합니다.
        """
        # 상품 존재 확인
        from products.models import Product
        get_object_or_404(Product, id=product_id)
        
        # 인증되지 않은 경우: has_review False로 고정 응답
        if not request.user or not request.user.is_authenticated:
            response_data = {
                'success': True,
                'product_id': product_id,
                'user_id': None,
                'has_review': False,
                'review_id': None
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # 사용자의 리뷰 작성 여부 확인 (인증된 사용자)
        user_review = Review.objects.filter(
            product_id=product_id,
            user=request.user
        ).first()
        
        has_review = user_review is not None
        review_id = user_review.id if user_review else None
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'product_id': product_id,
            'user_id': request.user.id,
            'has_review': has_review,
            'review_id': review_id
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class RandomProductsView(GenericAPIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="리뷰 작성 완료",
        description="리뷰 작성 완료 후 추천할 랜덤 제품 3개를 조회합니다. 제품 사진, 회사명, 제품명을 포함합니다.",
        responses={
            200: OpenApiResponse(
                description='랜덤 제품 목록 조회 성공',
                examples=[
                    OpenApiExample(
                        '성공 예시',
                        value={
                            "success": True,
                            "products": [
                                {
                                    "id": 15,
                                    "name": "제품명제품명제품명제품명 제품명 제품...",
                                    "company": "희세명",
                                    "image": "https://s3.amazonaws.com/bucket/product15.jpg"
                                },
                                {
                                    "id": 42,
                                    "name": "포도포도맛 쉐이크",
                                    "company": "(주)포도포도",
                                    "image": "https://s3.amazonaws.com/bucket/product42.jpg"
                                },
                                {
                                    "id": 73,
                                    "name": "[체지방 감소 인기대란] 포도컷",
                                    "company": "오늘부터다시",
                                    "image": "https://s3.amazonaws.com/bucket/product73.jpg"
                                }
                            ]
                        }
                    )
                ]
            )
        },
        tags=['리뷰']
    )
    def get(self, request):
        """
        랜덤 제품 3개를 조회합니다.
        """
        # 제품 이미지와 함께 랜덤 제품 3개 조회
        from products.models import Product
        import random
        
        # 모든 제품 중에서 랜덤하게 3개 선택 (이미지 유무 관계없이)
        all_products = Product.objects.all().prefetch_related('images')
        
        # 제품이 없는 경우 처리
        total_products = all_products.count()
        print(f"DEBUG: 총 제품 수: {total_products}")
        
        if total_products == 0:
            response_data = {
                'success': True,
                'products': []
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        # 랜덤하게 3개 선택 (제품 수가 3개 미만이면 전체 선택)
        sample_size = min(3, total_products)
        print(f"DEBUG: 선택할 제품 수: {sample_size}")
        random_products = random.sample(list(all_products), sample_size)
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'products': []
        }
        
        for product in random_products:
            first_image = product.images.first()
            product_data = {
                'id': product.id,
                'name': product.name,
                'company': product.company,
                'image': first_image.url if first_image else ''
            }
            response_data['products'].append(product_data)
        
        return Response(response_data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class ReviewCompleteView(GenericAPIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="리뷰 작성 완료",
        description="리뷰 작성 완료 확인",
    )
    def get(self, request):
        return Response({'success': True}, status=status.HTTP_200_OK)