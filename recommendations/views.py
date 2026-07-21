import logging

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from recommendations.models import UserSurvey, SavedRecommendation
from recommendations.serializers.saved import SaveRecommendationSerializer, SavedRecommendationSerializer
from recommendations.serializers.survey import SurveySerializer
from recommendations.services.recommendation import get_recommendations
logger = logging.getLogger(__name__)

class RecommendationView(APIView):
    """설문 응답을 받아 추천 결과 반환 (저장 X)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="맞춤 성분 추천 조회",
        description=(
                "설문 응답(라이프스타일 프로필)을 받아 Gemini 기반으로 성분 3개를 추천합니다. "
                "추천 결과는 저장되지 않으며, 별도로 PUT /api/recommendations/saved/ 를 호출해야 저장됩니다. "
                "설문 응답 자체는 유저당 1건으로 기록되며, 재요청 시 이전 응답을 덮어씁니다."
        ),
        request=SurveySerializer,
        responses={
            200: OpenApiResponse(
                description="추천 성공",
                examples=[
                    OpenApiExample(
                        "성공 예시",
                        value={
                            "count": 3,
                            "recommendations": [
                                {
                                    "ingredient_id": 12,
                                    "ingredient_name": "가르시니아캄보지아(HCA)",
                                    "intro": "탄수화물이 지방으로 합성되는 것을 억제하는 성분입니다.",
                                    "reason": "체지방 감소 목표에 적합한 성분입니다.",
                                    "fit_score": 95,
                                    "products": [
                                        {
                                            "id": 101,
                                            "name": "뉴트리원 가르시니아",
                                            "company": "뉴트리원",
                                            "thumbnail": "https://s3.amazonaws.com/bucket/image1.jpg",
                                        }
                                    ],
                                }
                            ],
                        },
                    )
                ],
            ),
            400: OpenApiResponse(description="설문 응답 형식 오류"),
            503: OpenApiResponse(
                description="추천 생성 실패 (Gemini API 오류)",
                examples=[
                    OpenApiExample(
                        "실패 예시",
                        value={"error": "추천 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
                    )
                ],
            ),
        },
        tags=["추천"],
    )
    def post(self, request):
        serializer = SurveySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        survey = serializer.validated_data

        # 설문 응답 기록 (유저당 1건, 재추천 시 덮어씀)
        UserSurvey.objects.update_or_create(
            user=request.user,
            defaults={"answers": survey},
        )

        try:
            recommendations = get_recommendations(survey)
        except Exception:
            logger.exception("추천 생성 실패")
            return Response(
                {"error": "추천 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "count": len(recommendations),
            "recommendations": recommendations,
        })

class SavedRecommendationView(APIView):
    """저장된 추천 (유저당 1건) - 저장 / 조회"""

    permission_classes = [IsAuthenticated]

    # 저장하기
    @extend_schema(
        summary="추천 결과 저장",
        description=(
                "POST /api/recommendations/ 응답으로 받은 성분 목록을 저장합니다. "
                "유저당 1건만 저장 가능하며, 기존 저장분이 있으면 새 값으로 교체됩니다."
        ),
        request=SaveRecommendationSerializer,
        responses={
            200: OpenApiResponse(
                response=SavedRecommendationSerializer,
                description="저장 성공",
                examples=[
                    OpenApiExample(
                        "성공 예시",
                        value={
                            "id": 7,
                            "created_at": "2026-07-18T10:00:00Z",
                            "updated_at": "2026-07-18T10:00:00Z",
                            "items": [
                                {
                                    "ingredient_id": 12,
                                    "ingredient_name": "가르시니아캄보지아(HCA)",
                                    "intro": "탄수화물이 지방으로 합성되는 것을 억제하는 성분입니다.",
                                    "reason": "체지방 감소 목표에 적합한 성분입니다.",
                                    "fit_score": 95,
                                    "rank": 1,
                                }
                            ],
                        },
                    )
                ],
            ),
            400: OpenApiResponse(description="요청 형식 오류 (성분 개수, 존재하지 않는 성분 등)"),
        },
        tags=["추천"],
    )
    def put(self, request):
        serializer = SaveRecommendationSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        recommendations = serializer.save()

        return Response(SavedRecommendationSerializer(recommendations).data)

    # 저장된 추천 조회
    @extend_schema(
        summary="저장된 추천 조회",
        description="현재 로그인한 사용자가 저장해둔 추천 결과를 조회합니다. 저장된 것이 없으면 saved 값이 null로 반환됩니다.",
        responses={
            200: OpenApiResponse(
                description="조회 성공 (저장 여부와 무관하게 200)",
                examples=[
                    OpenApiExample(
                        "저장된 것이 있는 경우",
                        value={
                            "saved": {
                                "id": 7,
                                "created_at": "2026-07-18T10:00:00Z",
                                "updated_at": "2026-07-18T10:00:00Z",
                                "items": [
                                    {
                                        "ingredient_id": 12,
                                        "ingredient_name": "가르시니아캄보지아(HCA)",
                                        "intro": "탄수화물이 지방으로 합성되는 것을 억제하는 성분입니다.",
                                        "reason": "체지방 감소 목표에 적합한 성분입니다.",
                                        "fit_score": 95,
                                        "rank": 1,
                                    }
                                ],
                            }
                        },
                    ),
                    OpenApiExample(
                        "저장된 것이 없는 경우",
                        value={"saved": None},
                    ),
                ],
            ),
        },
        tags=["추천"],
    )
    def get(self, request):
        recommendation = (
            SavedRecommendation.objects
            .filter(user=request.user)
            .prefetch_related("items__ingredient")
            .first()
        )

        if recommendation is None:
            return Response({"saved": None})

        return Response({"saved": SavedRecommendationSerializer(recommendation).data})