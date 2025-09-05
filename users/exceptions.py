from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # 기본 DRF exception 처리
    response = exception_handler(exc, context)

    if response is not None:
        # ValidationError 같은 경우 처리
        if isinstance(response.data, dict):
            # 메시지를 하나로 합치기
            message = None
            if "non_field_errors" in response.data:
                message = " ".join(response.data["non_field_errors"])
            elif "detail" in response.data:
                message = response.data["detail"]
            else:
                # 필드별 에러 처리 -> key 제거
                key, value = list(response.data.items())[0]
                message = f"{', '.join(value)}"

            response.data = {
                "success": False,
                "message": message,
            }
        else:
            # 그 외 예상 못한 에러
            response.data = {
                "success": False,
                "message": str(response.data),
            }

    else:
        # 완전히 처리 못한 예외
        return Response(
            {"success": False, "message": "서버 내부 오류가 발생했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
