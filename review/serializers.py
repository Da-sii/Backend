from rest_framework import serializers
from .models import Review, ReviewImage

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
    original_url = serializers.URLField()
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
        child=serializers.URLField(),
        min_length=1,
        max_length=10,
        help_text="업로드할 이미지 URL 목록 (최대 10개)"
    )
    
    def validate_urls(self, value):
        if not value:
            raise serializers.ValidationError("업로드할 URL이 필요합니다.")
        
        # URL 형식 검증
        for url in value:
            if not url.strip():
                raise serializers.ValidationError("빈 URL은 허용되지 않습니다.")
        
        return value

class ProductReviewImagesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    product_id = serializers.IntegerField()
    total_images = serializers.IntegerField()
    image_urls = serializers.ListField(
        child=serializers.CharField(),
        help_text="해당 상품의 모든 리뷰 이미지 URL 목록"
    )
