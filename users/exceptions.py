from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import traceback

def custom_exception_handler(exc, context):
    # 에러 디버깅 로그 추가(배포 시, 삭제 필요)
    print("=== Custom Exception Handler ===")
    print("Exception type:", type(exc))
    print("Exception message:", str(exc))
    traceback.print_exc()
    print("Context:", context)
    print("===============================")

    # 기본 DRF exception 처리
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(response.data, dict):
            message = None

            if "non_field_errors" in response.data:
                value = response.data["non_field_errors"]
                if isinstance(value, list):
                    message = " ".join(map(str, value))
                else:
                    message = str(value)

            elif "detail" in response.data:
                message = str(response.data["detail"])

            else:
                # 필드별 에러 처리 (첫 번째 항목만)
                key, value = list(response.data.items())[0]
                if isinstance(value, list):
                    message = ", ".join(map(str, value))
                else:
                    message = str(value)

            response.data = {
                "success": False,
                "message": message or "알 수 없는 오류가 발생했습니다.",
            }
        else:
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
