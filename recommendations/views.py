from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from recommendations.services.recommendation import get_recommendations


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # UserProfile 존재 여부 확인
        if not hasattr(request.user, 'profile'):
            return Response(
                {"error": "온보딩을 먼저 완료해주세요."},
                status = status.HTTP_404_NOT_FOUND
            )

        # 추천 실행
        try:
            recommendations = get_recommendations(request.user.profile)
        except Exception as e:
            return Response(
                {"error": "추천 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
                status = status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # fit_score 기준 내림차순 정렬 (Gemini가 정렬 안 했을 경우)
        recommendations = sorted(
            recommendations,
            key = lambda x: x["fit_score"],
            reverse = True
        )

        return Response({
            "count": len(recommendations),
            "recommendations": recommendations,
        })