from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rate', 'review']
    
    def validate_rate(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("별점은 1~5 사이여야 합니다.")
        return value
    
    def validate_review(self, value):
        if len(value.strip()) < 20 and len(value.strip()) > 1000:
            raise serializers.ValidationError("리뷰는 최소 20자 이상 최대 1000자 이하로 작성해주세요.")
        return value
