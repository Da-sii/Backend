from rest_framework import serializers
from .models import Review, ReviewImage, ReviewReport, ReviewReportReason

class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['url']

class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)
    date = serializers.DateField(read_only=True)
    
    class Meta:
        model = Review
        fields = ['rate', 'date', 'review', 'images']
    
    def validate_rate(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("별점은 1~5 사이여야 합니다.")
        return value
    
    def validate_review(self, value):
        if len(value.strip()) < 20 or len(value.strip()) > 1000:
            raise serializers.ValidationError("리뷰는 최소 20자 이상 최대 1000자 이하로 작성해주세요.")
        return value

class ReviewListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    reviews = serializers.DictField(
        child=ReviewSerializer()
    )

class ReviewCreateResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    review_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    rate = serializers.IntegerField()
    review = serializers.CharField()

class ReviewUpdateResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    review_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    rate = serializers.IntegerField()
    review = serializers.CharField()

class PresignedUrlSerializer(serializers.Serializer):
    image_id = serializers.IntegerField()
    original_url = serializers.CharField()
    upload_url = serializers.URLField()
    final_url = serializers.URLField()
    filename = serializers.CharField()

class ReviewImageUploadResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    presigned_urls = PresignedUrlSerializer(many=True)

class ReviewImageDeleteResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    image_id = serializers.IntegerField()
    filename = serializers.CharField()

class ReviewImageUploadRequestSerializer(serializers.Serializer):
    urls = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=10,
        help_text="업로드할 이미지 파일명 또는 URL 목록 (최대 10개)"
    )
    
    def validate_urls(self, value):
        if not value:
            raise serializers.ValidationError("업로드할 파일명이 필요합니다.")
        
        # 파일명 형식 검증
        for filename in value:
            if not filename.strip():
                raise serializers.ValidationError("빈 파일명은 허용되지 않습니다.")
        
        return value

class ProductReviewImagesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    product_id = serializers.IntegerField()
    total_images = serializers.IntegerField()
    image_urls = serializers.ListField(
        child=serializers.CharField(),
        help_text="해당 상품의 모든 리뷰 이미지 URL 목록"
    )

class ProductRatingStatsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    product_id = serializers.IntegerField()
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="별점별 리뷰 개수 (1점, 2점, 3점, 4점, 5점)"
    )

class ReviewImageDetailSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source='review.user.nickname', read_only=True)
    rate = serializers.IntegerField(source='review.rate', read_only=True)
    date = serializers.DateField(source='review.date', read_only=True)
    review = serializers.CharField(source='review.review', read_only=True)
    
    class Meta:
        model = ReviewImage
        fields = ['url', 'nickname', 'rate', 'date', 'review']

class ReviewImageDetailResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    image_id = serializers.IntegerField()
    review_info = ReviewImageDetailSerializer()

class UserReviewsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    user_id = serializers.IntegerField()
    total_reviews = serializers.IntegerField()
    reviews = ReviewSerializer(many=True)

class ReviewDeleteResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    review_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    product_id = serializers.IntegerField()

class ProductInfoSerializer(serializers.Serializer):
    """제품 정보 시리얼라이저"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    company = serializers.CharField()
    image = serializers.SerializerMethodField()
    
    def get_image(self, obj):
        """첫 번째 이미지 URL을 반환"""
        first_image = obj.images.first()
        return first_image.url if first_image else ''

class MyPageReviewSerializer(serializers.ModelSerializer):
    """마이페이지용 리뷰 시리얼라이저"""
    images = ReviewImageSerializer(many=True, read_only=True)
    product_info = ProductInfoSerializer(source='product', read_only=True)
    review_id = serializers.IntegerField(source='id', read_only=True)
    date = serializers.DateField(read_only=True)
    
    class Meta:
        model = Review
        fields = ['review_id', 'rate', 'date', 'review', 'updated', 'images', 'product_info']
