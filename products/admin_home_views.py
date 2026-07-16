"""/admin/home 페이지 뷰 모음.

카테고리(대/중/소분류)·제품 목록·배너·원료(기능성/기타) 관리와 검수용
스타일가이드 뷰를 담는다. 기존 admin_views.py(구 /admin 콘솔)는 건드리지 않는다.
"""

import json
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Prefetch, ProtectedError
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from common.models import Banner, BannerDetail
from common.utils import upload_banner_to_s3
from products.models import (
    BigCategory,
    CategoryProduct,
    Ingredient,
    IngredientGuide,
    MiddleCategory,
    OtherIngredient,
    Product,
    ProductImage,
    ProductIngredient,
    ProductOtherIngredient,
    ProductRequest,
    SmallCategory,
)
from products.utils import upload_images_to_s3
from users.models import User


# ---------------------------------------------------------------------------
# 부분 로딩(SPA식 탭 전환) 지원 렌더 헬퍼
# ---------------------------------------------------------------------------
def _ah_render(request, template, context=None):
    """admin_home 페이지 렌더 공통 진입점.

    partial-nav.js 가 보낸 부분 로딩 요청(X-Partial-Nav 헤더)이면 전체 문서/상단 탭 바
    없이 콘텐츠만 렌더하도록 base_template 을 셸(_partial_base.html)로 바꾼다.
    일반(직접) 요청이면 전체 레이아웃(base.html)을 그대로 사용한다.
    페이지 템플릿은 `{% extends base_template|default:"admin_home/base.html" %}` 로 확장한다.
    """
    ctx = dict(context or {})
    if request.headers.get("X-Partial-Nav") == "1":
        ctx["base_template"] = "admin_home/_partial_base.html"
    else:
        ctx["base_template"] = "admin_home/base.html"
    return render(request, template, ctx)


# ---------------------------------------------------------------------------
# 스타일가이드에 뿌릴 토큰 데이터 (검수 전용)
# 스와치 배경은 CSS 변수(var(--color-...))로 렌더 → 토큰이 실제로 해석되는지 검수.
# ---------------------------------------------------------------------------
def _scale(prefix, steps):
    return [
        {"name": f"{prefix}-{s}", "hex": hex_, "cssvar": f"var(--color-{prefix}-{s})"}
        for s, hex_ in steps
    ]


COLOR_SCALES = [
    {
        "title": "Primary — Green",
        "main": "green-500",
        "swatches": _scale(
            "green",
            [
                ("50", "#EAFAF2"), ("100", "#D5F6E4"), ("200", "#ACECCA"),
                ("300", "#82E3AF"), ("400", "#58DA95"), ("500", "#50D88F"),
                ("600", "#25A762"), ("700", "#1C7D49"), ("800", "#135331"),
                ("900", "#092A18"), ("950", "#05150C"),
            ],
        ),
    },
    {
        "title": "Sub — Blue",
        "main": "blue-400",
        "swatches": _scale(
            "blue",
            [
                ("50", "#E5F0FF"), ("100", "#CCE0FF"), ("200", "#99C2FF"),
                ("300", "#66A3FF"), ("400", "#5398FF"), ("500", "#3385FF"),
                ("600", "#0052CC"), ("700", "#003D99"), ("800", "#002966"),
                ("900", "#001433"), ("950", "#000A1A"),
            ],
        ),
    },
    {
        "title": "Gray",
        "main": "gray-0",
        "swatches": _scale(
            "gray",
            [
                ("0", "#FFFFFF"), ("50", "#F1F2F3"), ("100", "#E4E6E7"),
                ("200", "#C9CCCF"), ("300", "#AEB3B7"), ("400", "#939A9F"),
                ("500", "#60676C"), ("600", "#484D51"), ("700", "#363A3D"),
                ("800", "#303336"), ("900", "#181A1B"), ("950", "#0C0D0E"),
            ],
        ),
    },
]

ETC_COLORS = [
    {"name": "kakao", "hex": "#FEE500", "cssvar": "var(--color-kakao)"},
    {"name": "error", "hex": "#FF3A4A", "cssvar": "var(--color-error)"},
    {"name": "graybox", "hex": "#F6F5FA", "cssvar": "var(--color-graybox)"},
    {"name": "ok", "hex": "#9DD716", "cssvar": "var(--color-ok)"},
    {"name": "orange", "hex": "#ED9A01", "cssvar": "var(--color-orange)"},
    {"name": "star-yellow", "hex": "#F6C72B", "cssvar": "var(--color-star-yellow)"},
    {"name": "gradient-logo", "hex": "linear", "cssvar": "var(--gradient-logo)"},
    {"name": "gradient-bar", "hex": "linear", "cssvar": "var(--gradient-bar)"},
]

CALENDAR_COLORS = [
    {"name": "cal-lightorange", "hex": "#FEE8D4", "cssvar": "var(--color-cal-lightorange)"},
    {"name": "cal-orange", "hex": "#FD8F2A", "cssvar": "var(--color-cal-orange)"},
    {"name": "cal-lightpurple", "hex": "#EEDDF8", "cssvar": "var(--color-cal-lightpurple)"},
    {"name": "cal-purple", "hex": "#A954DD", "cssvar": "var(--color-cal-purple)"},
    {"name": "cal-lightpink", "hex": "#FBE2EB", "cssvar": "var(--color-cal-lightpink)"},
    {"name": "cal-pink", "hex": "#EA709C", "cssvar": "var(--color-cal-pink)"},
]

TYPE_SCALE = [
    {"cls": "text-display", "label": "display", "size": "36px", "lh": "1.2", "use": "Hero 헤드라인"},
    {"cls": "text-title-lg", "label": "title-lg", "size": "28px", "lh": "1.3", "use": "Headline"},
    {"cls": "text-title-md", "label": "title-md", "size": "24px", "lh": "1.35", "use": "Title"},
    {"cls": "text-title-sm", "label": "title-sm", "size": "21px", "lh": "1.4", "use": "Sub Title"},
    {"cls": "text-body-lg", "label": "text-lg", "size": "22px", "lh": "1.5", "use": "Body"},
    {"cls": "text-body", "label": "text-md", "size": "20px", "lh": "1.5", "use": "Body"},
    {"cls": "text-body-sm", "label": "text-sm", "size": "18px", "lh": "1.5", "use": "Body (최소)"},
    {"cls": "text-caption", "label": "caption", "size": "18px", "lh": "1.4", "use": "Caption (floor)"},
]


KST = ZoneInfo("Asia/Seoul")

# 미니 차트용 SVG 좌표계(누적 스파크라인). 실제 픽셀이 아닌 viewBox 단위.
_SPARK_W = 300
_SPARK_H = 64
_SPARK_PAD = 4  # 상하 여백(선 굵기가 잘리지 않게)


def _signup_chart(days=30):
    """users.User.created_at(가입일) 기준 최근 N일 가입 통계를 집계한다(읽기 전용).

    - KST(Asia/Seoul) 기준으로 날짜를 자른다(DB 는 UTC 저장이므로
      TruncDate 에 tzinfo 를 넘겨 KST 자정 경계로 보정).
    - 일자별 "신규 가입 수"와 그날까지의 "누적 총 회원 수"를 함께 만든다.
    - 외부 차트 라이브러리 없이 템플릿에서 CSS 바 + 인라인 SVG 로 그릴 수 있도록
      막대 높이(%)와 누적 스파크라인의 SVG 좌표까지 미리 계산해 돌려준다.
    """
    now_kst = timezone.now().astimezone(KST)
    today = now_kst.date()
    start_date = today - timedelta(days=days - 1)
    # 윈도 시작(=start_date 00:00 KST)을 aware datetime 으로 만들어 필터 경계로 사용
    start_dt = datetime.combine(start_date, time.min, tzinfo=KST)

    daily = (
        User.objects.filter(created_at__gte=start_dt)
        .annotate(day=TruncDate("created_at", tzinfo=KST))
        .values("day")
        .annotate(count=Count("id"))
    )
    counts_by_day = {row["day"]: row["count"] for row in daily}

    # 윈도 이전까지의 총 회원 수 → 누적선의 시작 기준값
    base_total = User.objects.filter(created_at__lt=start_dt).count()

    points = []
    cumulative = base_total
    for i in range(days):
        d = start_date + timedelta(days=i)
        new = counts_by_day.get(d, 0)
        cumulative += new
        points.append({"date": d, "new": new, "total": cumulative})

    new_max = max((p["new"] for p in points), default=0)
    total_min = min((p["total"] for p in points), default=0)
    total_max = max((p["total"] for p in points), default=0)
    total_span = total_max - total_min

    inner_h = _SPARK_H - _SPARK_PAD * 2
    step_x = _SPARK_W / (days - 1) if days > 1 else 0
    spark_coords = []
    for i, p in enumerate(points):
        # 막대 높이(%): 신규 가입 수를 최댓값 대비 비율로. 0 이어도 최소 높이는 CSS 에서 처리.
        p["bar_pct"] = round(p["new"] / new_max * 100) if new_max else 0
        x = round(i * step_x, 2)
        if total_span:
            y = round(_SPARK_PAD + (total_max - p["total"]) / total_span * inner_h, 2)
        else:
            y = round(_SPARK_H / 2, 2)
        p["x"] = x
        p["y"] = y
        spark_coords.append(f"{x},{y}")

    spark_points = " ".join(spark_coords)
    # 누적선 아래를 채우는 영역(폴리곤): 선 좌표 + 우하단·좌하단으로 닫는다.
    if spark_coords:
        spark_area = (
            f"0,{_SPARK_H} {spark_points} {_SPARK_W},{_SPARK_H}"
        )
    else:
        spark_area = ""

    return {
        "days": days,
        "points": points,
        "new_total": sum(p["new"] for p in points),
        "today_new": points[-1]["new"] if points else 0,
        "grand_total": cumulative,
        "start_date": start_date,
        "end_date": today,
        "spark_w": _SPARK_W,
        "spark_h": _SPARK_H,
        "spark_points": spark_points,
        "spark_area": spark_area,
    }


def _home_kpis(chart):
    """홈 대시보드 상단 KPI 스탯 타일용 집계(읽기 전용 count).

    카탈로그/회원 규모를 한눈에 보여준다. 각 타일은 label/value/icon 과
    선택적으로 관리 페이지로 가는 href 를 갖는다(_stat.html 컴포넌트가 렌더).
    오늘 신규 가입은 이미 계산된 signup_chart(chart) 값을 재사용한다.
    """
    return [
        {"label": "총 회원", "value": User.objects.count(), "icon": "👥"},
        {"label": "오늘 신규 가입", "value": chart["today_new"], "icon": "🌱"},
        {
            "label": "제품",
            "value": Product.objects.count(),
            "icon": "📦",
            "href": reverse("admin_home_product"),
        },
        {
            "label": "기능성 원료",
            "value": Ingredient.objects.count(),
            "icon": "🧪",
            "href": reverse("admin_home_ingredient"),
        },
        {
            "label": "기타 원료",
            "value": OtherIngredient.objects.count(),
            "icon": "🧴",
            "href": reverse("admin_home_ingredient_other"),
        },
        {
            "label": "소분류",
            "value": SmallCategory.objects.count(),
            "icon": "🗂️",
            "href": reverse("admin_home_category"),
        },
        {
            "label": "배너",
            "value": Banner.objects.count(),
            "icon": "🖼️",
            "href": reverse("admin_home_banner"),
        },
    ]


def home(request):
    """/admin/home 랜딩(홈). 로그인 후 진입 지점 — 대시보드 개요.

    상단에 카탈로그/회원 규모 KPI 스탯 타일을 두고, 그 아래 최근 30일 가입 추이
    미니 차트(신규 막대 + 누적 스파크라인)와 "제품 추가 요청" 위젯을 배치한다.
    제품 추가 요청은 사용자가 보낸 ProductRequest 목록으로, 위젯의 "전체 보기"가
    여는 모달에서 확인/삭제한다(action=delete). 모든 집계는 읽기 전용이다.
    """
    if request.method == "POST" and request.POST.get("action") == "delete":
        # AJAX(모달 내 삭제)면 JSON 으로 응답해 모달·리스트를 유지한 채 처리한다.
        # 일반 폼 제출이면 기존대로 메시지 + 리다이렉트로 폴백한다.
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        try:
            ProductRequest.objects.get(id=request.POST.get("id", "")).delete()
            if is_ajax:
                return JsonResponse({"ok": True})
            messages.success(request, "제품 추가 요청이 삭제되었습니다.")
        except (ProductRequest.DoesNotExist, ValueError):
            if is_ajax:
                return JsonResponse(
                    {"ok": False, "error": "제품 추가 요청을 찾을 수 없습니다."},
                    status=404,
                )
            messages.error(request, "제품 추가 요청을 찾을 수 없습니다.")
        return redirect("admin_home")

    product_requests = ProductRequest.objects.select_related("user").order_by(
        "-created_at"
    )
    chart = _signup_chart(30)
    return _ah_render(
        request,
        "admin_home/home.html",
        {
            "product_requests": product_requests,
            "signup_chart": chart,
            "kpis": _home_kpis(chart),
        },
    )


def styleguide(request):
    """디자인 토큰·컴포넌트 검수용 페이지. 실제 기능이 아니다."""
    context = {
        "color_scales": COLOR_SCALES,
        "etc_colors": ETC_COLORS,
        "calendar_colors": CALENDAR_COLORS,
        "type_scale": TYPE_SCALE,
    }
    return _ah_render(request, "admin_home/_styleguide.html", context)


# ---------------------------------------------------------------------------
# 카테고리 관리 — 대/중/소 통합 트리(category_tree) + 공통 헬퍼
# ---------------------------------------------------------------------------
def _get_big_category(request):
    """POST 의 id 로 BigCategory 를 찾고, 없으면 메시지를 남기고 None 반환."""
    try:
        return BigCategory.objects.get(id=request.POST.get("id", ""))
    except (BigCategory.DoesNotExist, ValueError):
        messages.error(request, "대분류를 찾을 수 없습니다.")
        return None


def _get_parent_big(request):
    """생성 대상의 상위 대분류(parent id)를 찾고, 없으면 메시지 후 None 반환."""
    try:
        return BigCategory.objects.get(id=request.POST.get("parent", ""))
    except (BigCategory.DoesNotExist, ValueError):
        messages.error(request, "상위 대분류를 찾을 수 없습니다.")
        return None


def _get_parent_middle(request):
    """생성 대상의 상위 중분류(parent id)를 찾고, 없으면 메시지 후 None 반환."""
    try:
        return MiddleCategory.objects.select_related("big_category").get(
            id=request.POST.get("parent", "")
        )
    except (MiddleCategory.DoesNotExist, ValueError):
        messages.error(request, "상위 중분류를 찾을 수 없습니다.")
        return None


def _handle_category_post(request):
    """트리 페이지의 생성/수정/삭제 POST 를 level+action 으로 분기 처리한다.

    level: big/middle/small, action: create/update/delete.
    이름 중복은 같은 부모 범위 안에서만 검사한다(대분류는 전역). 수정은 이름 변경만(이동 없음).
    삭제는 PROTECT(CategoryProduct) 때문에 하위 소분류-제품 연결을 먼저 지운 뒤 대상을
    삭제하면 CASCADE 로 하위가 정리된다.
    """
    level = request.POST.get("level", "")
    action = request.POST.get("action", "")
    name = request.POST.get("category", "").strip()

    if level == "big":
        if action == "create":
            if not name:
                messages.error(request, "대분류 이름을 입력해주세요.")
            elif BigCategory.objects.filter(category=name).exists():
                messages.error(request, f'"{name}" 대분류가 이미 존재합니다.')
            else:
                BigCategory.objects.create(category=name)
                messages.success(request, f'"{name}" 대분류가 추가되었습니다.')
        elif action == "update":
            cat = _get_big_category(request)
            if cat is not None:
                if not name:
                    messages.error(request, "대분류 이름을 입력해주세요.")
                elif (
                    BigCategory.objects.filter(category=name)
                    .exclude(id=cat.id)
                    .exists()
                ):
                    messages.error(request, f'"{name}" 대분류가 이미 존재합니다.')
                else:
                    cat.category = name
                    cat.save()
                    messages.success(request, f'"{name}" 대분류가 수정되었습니다.')
        elif action == "delete":
            cat = _get_big_category(request)
            if cat is not None:
                label = cat.category
                # PROTECT(CategoryProduct) 때문에 소분류-제품 연결을 먼저 제거해야 삭제 가능
                small_cats = SmallCategory.objects.filter(
                    middle_category__big_category=cat
                )
                CategoryProduct.objects.filter(category__in=small_cats).delete()
                cat.delete()  # CASCADE 로 중분류·소분류 정리
                messages.success(request, f'"{label}" 대분류가 삭제되었습니다.')
        else:
            messages.error(request, "알 수 없는 요청입니다.")

    elif level == "middle":
        if action == "create":
            big = _get_parent_big(request)
            if big is not None:
                if not name:
                    messages.error(request, "중분류 이름을 입력해주세요.")
                elif MiddleCategory.objects.filter(
                    big_category=big, category=name
                ).exists():
                    messages.error(
                        request, f'"{big.category} - {name}" 중분류가 이미 존재합니다.'
                    )
                else:
                    MiddleCategory.objects.create(big_category=big, category=name)
                    messages.success(
                        request, f'"{big.category} - {name}" 중분류가 추가되었습니다.'
                    )
        elif action == "update":
            mid = _get_middle_category(request)
            if mid is not None:
                if not name:
                    messages.error(request, "중분류 이름을 입력해주세요.")
                elif (
                    MiddleCategory.objects.filter(
                        big_category=mid.big_category, category=name
                    )
                    .exclude(id=mid.id)
                    .exists()
                ):
                    messages.error(
                        request,
                        f'"{mid.big_category.category} - {name}" 중분류가 이미 존재합니다.',
                    )
                else:
                    mid.category = name
                    mid.save()
                    messages.success(
                        request,
                        f'"{mid.big_category.category} - {name}" 중분류가 수정되었습니다.',
                    )
        elif action == "delete":
            mid = _get_middle_category(request)
            if mid is not None:
                label = f"{mid.big_category.category} - {mid.category}"
                small_cats = SmallCategory.objects.filter(middle_category=mid)
                CategoryProduct.objects.filter(category__in=small_cats).delete()
                mid.delete()  # CASCADE 로 소분류 정리
                messages.success(request, f'"{label}" 중분류가 삭제되었습니다.')
        else:
            messages.error(request, "알 수 없는 요청입니다.")

    elif level == "small":
        if action == "create":
            mid = _get_parent_middle(request)
            if mid is not None:
                if not name:
                    messages.error(request, "소분류 이름을 입력해주세요.")
                elif SmallCategory.objects.filter(
                    middle_category=mid, category=name
                ).exists():
                    messages.error(request, f'"{name}" 소분류가 이미 존재합니다.')
                else:
                    SmallCategory.objects.create(middle_category=mid, category=name)
                    messages.success(request, f'"{name}" 소분류가 추가되었습니다.')
        elif action == "update":
            small = _get_small_category(request)
            if small is not None:
                if not name:
                    messages.error(request, "소분류 이름을 입력해주세요.")
                elif (
                    SmallCategory.objects.filter(
                        middle_category=small.middle_category, category=name
                    )
                    .exclude(id=small.id)
                    .exists()
                ):
                    messages.error(request, f'"{name}" 소분류가 이미 존재합니다.')
                else:
                    small.category = name
                    small.save()
                    messages.success(request, f'"{name}" 소분류가 수정되었습니다.')
        elif action == "delete":
            small = _get_small_category(request)
            if small is not None:
                label = small.category
                # PROTECT(CategoryProduct) 때문에 제품 연결을 먼저 제거해야 삭제 가능
                CategoryProduct.objects.filter(category=small).delete()
                small.delete()
                messages.success(request, f'"{label}" 소분류가 삭제되었습니다.')
        else:
            messages.error(request, "알 수 없는 요청입니다.")

    else:
        messages.error(request, "알 수 없는 요청입니다.")

    return redirect("admin_home_category")


def category_tree(request):
    """카테고리 · 대/중/소 통합 트리 (목록 + 생성/수정/삭제).

    GET 은 대→중→소를 항상 펼친 트리로 조립해 렌더한다(빈 가지 포함, 소분류엔 제품 연결 수).
    POST 는 _handle_category_post 로 위임한다.
    """
    if request.method == "POST":
        return _handle_category_post(request)

    bigs = BigCategory.objects.prefetch_related(
        Prefetch(
            "middle_categories",
            queryset=MiddleCategory.objects.order_by("id"),
        ),
        Prefetch(
            "middle_categories__small_categories",
            queryset=SmallCategory.objects.order_by("id").annotate(
                product_count=Count("category_products", distinct=True)
            ),
        ),
    ).order_by("id")
    return _ah_render(request, "admin_home/category_tree.html", {"bigs": bigs})


# ---------------------------------------------------------------------------
# 카테고리 관리 — 중/소분류 조회 헬퍼 (위 category_tree POST 처리에서 사용)
# ---------------------------------------------------------------------------
def _get_middle_category(request):
    """POST 의 id 로 MiddleCategory 를 찾고, 없으면 메시지를 남기고 None 반환."""
    try:
        return MiddleCategory.objects.select_related("big_category").get(
            id=request.POST.get("id", "")
        )
    except (MiddleCategory.DoesNotExist, ValueError):
        messages.error(request, "중분류를 찾을 수 없습니다.")
        return None


def _get_small_category(request):
    """POST 의 id 로 SmallCategory 를 찾고, 없으면 메시지를 남기고 None 반환."""
    try:
        return SmallCategory.objects.select_related(
            "middle_category__big_category"
        ).get(id=request.POST.get("id", ""))
    except (SmallCategory.DoesNotExist, ValueError):
        messages.error(request, "소분류를 찾을 수 없습니다.")
        return None


# ---------------------------------------------------------------------------
# 제품 관리 — 목록 + 추가/수정(모달)
# 추가·수정 모두 admin_home 모달에서 처리한다(기존 admin 편집기로 이동하지 않음).
# 성분/기타원료/카테고리 연결 생성은 _save_product_relations 로 create·update 공용,
# update 는 기존 연결을 지운 뒤 다시 만드는 replace-all 방식이다.
# ---------------------------------------------------------------------------
def _save_product_relations(product, request):
    """POST 배열로 제품의 성분/기타원료/카테고리 연결을 생성한다(create·update 공용).

    같은 항목을 중복 선택해도 unique/중복이 생기지 않도록 seen 집합으로 거른다.
    update 에서는 호출 전에 기존 연결(ProductIngredient/ProductOtherIngredient/
    CategoryProduct)을 모두 지워 replace-all 로 동작시킨다(링크 행 삭제는 PROTECT 무관).
    """
    # 성분 + 용량 → ProductIngredient
    seen_ing = set()
    for ingredient_id, amount in zip(
        request.POST.getlist("ingredient_ids[]"),
        request.POST.getlist("amounts[]"),
    ):
        ingredient_id = ingredient_id.strip()
        amount = amount.strip()
        if not (ingredient_id and amount) or ingredient_id in seen_ing:
            continue
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
        except (Ingredient.DoesNotExist, ValueError):
            continue
        seen_ing.add(ingredient_id)
        ProductIngredient.objects.create(
            product=product, ingredient=ingredient, amount=amount
        )

    # 기타 원료 → ProductOtherIngredient
    seen_oi = set()
    for oi_id in request.POST.getlist("other_ingredient_ids[]"):
        oi_id = oi_id.strip()
        if not oi_id or oi_id in seen_oi:
            continue
        try:
            oi = OtherIngredient.objects.get(id=oi_id)
        except (OtherIngredient.DoesNotExist, ValueError):
            continue
        seen_oi.add(oi_id)
        ProductOtherIngredient.objects.create(product=product, other_ingredient=oi)

    # 소분류 카테고리 → CategoryProduct
    seen_cat = set()
    for category_id in request.POST.getlist("category_ids[]"):
        category_id = category_id.strip()
        if not category_id or category_id in seen_cat:
            continue
        try:
            category = SmallCategory.objects.get(id=category_id)
        except (SmallCategory.DoesNotExist, ValueError):
            continue
        seen_cat.add(category_id)
        CategoryProduct.objects.create(product=product, category=category)


def product_list(request):
    """제품 리스트 + 제품 추가(create)/수정(update) — 모두 모달에서 처리.

    - action=create: Product 기본필드 + 이미지 업로드 + 성분/기타원료/카테고리 연결 생성.
    - action=update: 기본필드·이미지(선택 삭제/추가) 갱신 + 연결 replace-all.
    두 경로 모두 연결 생성은 _save_product_relations 공용 헬퍼를 쓴다.
    목록에는 모달 렌더용 선택지(ingredients/other_ingredients/small_categories)와
    행별 상세/수정 prefill 데이터(product.edit_data, json_script 용)를 함께 내려준다.
    """
    if request.method == "POST" and request.POST.get("action") == "create":
        name = request.POST.get("name", "").strip()
        company = request.POST.get("company", "").strip()
        product_type = request.POST.get("productType", "").strip()
        coupang = request.POST.get("coupang", "").strip() or None

        if not all([name, company, product_type]):
            messages.error(request, "모든 필수 항목을 입력해주세요.")
            return redirect("admin_home_product")

        try:
            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    company=company,
                    productType=product_type,
                    coupang=coupang,
                )

                image_files = request.FILES.getlist("image_files")
                if image_files:
                    ProductImage.objects.bulk_create(
                        upload_images_to_s3(product, image_files)
                    )

                _save_product_relations(product, request)

            messages.success(request, f'"{name}" 제품이 추가되었습니다.')
        except Exception as e:
            messages.error(request, f"오류가 발생했습니다: {str(e)}")
        return redirect("admin_home_product")

    if request.method == "POST" and request.POST.get("action") == "update":
        # 상세/수정 모달 저장 — 기본필드 + 이미지(선택 삭제/추가) + 연결 replace-all.
        try:
            product = Product.objects.get(id=request.POST.get("id", ""))
        except (Product.DoesNotExist, ValueError):
            messages.error(request, "제품을 찾을 수 없습니다.")
            return redirect("admin_home_product")

        name = request.POST.get("name", "").strip()
        company = request.POST.get("company", "").strip()
        product_type = request.POST.get("productType", "").strip()
        coupang = request.POST.get("coupang", "").strip() or None

        if not all([name, company, product_type]):
            messages.error(request, "모든 필수 항목을 입력해주세요.")
            return redirect("admin_home_product")

        try:
            with transaction.atomic():
                product.name = name
                product.company = company
                product.productType = product_type
                product.coupang = coupang
                product.save()

                # 이미지 — 체크한 기존 이미지 삭제 + 새 이미지 업로드/추가
                delete_ids = [
                    i for i in request.POST.getlist("delete_image_ids[]") if i.strip()
                ]
                if delete_ids:
                    ProductImage.objects.filter(
                        id__in=delete_ids, product=product
                    ).delete()
                new_images = request.FILES.getlist("image_files")
                if new_images:
                    ProductImage.objects.bulk_create(
                        upload_images_to_s3(product, new_images)
                    )

                # 성분/기타원료/카테고리 연결 — 기존을 지우고 폼 값으로 다시 생성(replace-all)
                ProductIngredient.objects.filter(product=product).delete()
                ProductOtherIngredient.objects.filter(product=product).delete()
                CategoryProduct.objects.filter(product=product).delete()
                _save_product_relations(product, request)

            messages.success(request, f'"{name}" 제품이 수정되었습니다.')
        except Exception as e:
            messages.error(request, f"오류가 발생했습니다: {str(e)}")
        return redirect("admin_home_product")

    products = Product.objects.annotate(
        image_count=Count("images", distinct=True),
        ingredient_count=Count("ingredients", distinct=True),
        category_count=Count("category_products", distinct=True),
    ).prefetch_related(
        "images",
        "ingredients__ingredient",
        "category_products__category__middle_category__big_category",
        "product_other_ingredients__other_ingredient",
    ).order_by("-id")

    # 상세/수정 모달 prefill 용 제품별 데이터 — 행마다 json_script 로 심어 JS 가 읽는다.
    # (prefetch 된 관계만 사용하므로 추가 쿼리 없음)
    products = list(products)
    for p in products:
        p.data_id = f"product-data-{p.id}"
        p.edit_data = {
            "id": p.id,
            "name": p.name,
            "company": p.company,
            "productType": p.productType,
            "coupang": p.coupang or "",
            "images": [{"id": img.id, "url": img.url} for img in p.images.all()],
            "ingredients": [
                {"id": pi.ingredient_id, "amount": pi.amount}
                for pi in p.ingredients.all()
            ],
            "others": [
                {"id": poi.other_ingredient_id}
                for poi in p.product_other_ingredients.all()
            ],
            "categories": [{"id": cp.category_id} for cp in p.category_products.all()],
        }

    # 모달 추가/수정 폼 렌더용 선택지
    ingredients = Ingredient.objects.all().order_by("id")
    other_ingredients = OtherIngredient.objects.all().order_by("name")
    small_categories = (
        SmallCategory.objects.select_related("middle_category__big_category")
        .all()
        .order_by(
            "middle_category__big_category__id",
            "middle_category__id",
            "id",
        )
    )

    return _ah_render(
        request,
        "admin_home/product_list.html",
        {
            "products": products,
            "ingredients": ingredients,
            "other_ingredients": other_ingredients,
            "small_categories": small_categories,
        },
    )


# ---------------------------------------------------------------------------
# 배너 관리 — Banner (목록/추가/삭제). 상세(BannerDetail)는 별도.
# 기존 common admin 배너 기능(common.admin.admin_views)을 /admin/home 로 이식.
# ---------------------------------------------------------------------------
def _parse_order(raw, default=1):
    """order 입력값을 1 이상의 정수로 정규화한다."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value >= 1 else default


def banner_list(request):
    """배너 관리 — 목록/추가/삭제.

    이미지는 common.utils.upload_banner_to_s3 로 S3 업로드 후 URL 을 저장한다.
    Banner.order 는 고유(unique)라 중복 시 IntegrityError → 에러 메시지로 안내한다.
    (배너별 상세 이미지 관리는 banner_detail_* 뷰에서 담당)
    """
    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "create":
            image = request.FILES.get("image")
            order = _parse_order(request.POST.get("order"))
            dup_msg = f"순서 {order}은(는) 이미 사용 중입니다. 다른 순서를 입력해주세요."
            if not image:
                messages.error(request, "배너 이미지를 선택해주세요.")
            elif Banner.objects.filter(order=order).exists():
                # 중복이면 S3 업로드 전에 막아 불필요한 업로드/고아 파일을 피한다.
                messages.error(request, dup_msg)
            else:
                image_url = upload_banner_to_s3(image)
                try:
                    with transaction.atomic():
                        Banner.objects.create(image_url=image_url, order=order)
                    messages.success(request, "배너가 추가되었습니다.")
                except IntegrityError:
                    # 동시 요청 경합 등으로 order 가 중복된 경우의 안전망
                    messages.error(request, dup_msg)
            return redirect("admin_home_banner")

        if action == "delete":
            try:
                Banner.objects.get(id=request.POST.get("id", "")).delete()
                messages.success(request, "배너가 삭제되었습니다.")
            except (Banner.DoesNotExist, ValueError):
                messages.error(request, "배너를 찾을 수 없습니다.")
            return redirect("admin_home_banner")

        if action == "toggle_active":
            try:
                banner = Banner.objects.get(id=request.POST.get("id", ""))
            except (Banner.DoesNotExist, ValueError):
                messages.error(request, "배너를 찾을 수 없습니다.")
                return redirect("admin_home_banner")
            banner.is_active = not banner.is_active
            banner.save(update_fields=["is_active"])
            state = "노출" if banner.is_active else "숨김"
            messages.success(request, f"배너 #{banner.id}를 {state} 상태로 변경했습니다.")
            return redirect("admin_home_banner")

        if action == "detail_create":
            try:
                banner = Banner.objects.get(id=request.POST.get("banner_id", ""))
            except (Banner.DoesNotExist, ValueError):
                messages.error(request, "배너를 찾을 수 없습니다.")
                return redirect("admin_home_banner")
            image = request.FILES.get("detail_image")
            order = _parse_order(request.POST.get("order"))
            dup_msg = (
                f"배너 #{banner.id}에 순서 {order}은(는) 이미 사용 중입니다. "
                "다른 순서를 입력해주세요."
            )
            if not image:
                messages.error(request, "상세 이미지를 선택해주세요.")
            elif BannerDetail.objects.filter(banner=banner, order=order).exists():
                messages.error(request, dup_msg)
            else:
                detail_image_url = upload_banner_to_s3(image)
                try:
                    with transaction.atomic():
                        BannerDetail.objects.create(
                            banner=banner,
                            detail_image_url=detail_image_url,
                            order=order,
                        )
                    messages.success(request, "상세 이미지가 추가되었습니다.")
                except IntegrityError:
                    messages.error(request, dup_msg)
            return redirect("admin_home_banner")

        if action == "detail_delete":
            try:
                BannerDetail.objects.get(id=request.POST.get("id", "")).delete()
                messages.success(request, "상세 이미지가 삭제되었습니다.")
            except (BannerDetail.DoesNotExist, ValueError):
                messages.error(request, "상세 이미지를 찾을 수 없습니다.")
            return redirect("admin_home_banner")

        messages.error(request, "알 수 없는 요청입니다.")
        return redirect("admin_home_banner")

    banners = Banner.objects.prefetch_related("details").all()
    next_order = (Banner.objects.aggregate(m=Max("order"))["m"] or 0) + 1
    return _ah_render(
        request,
        "admin_home/banner_list.html",
        {"banners": banners, "next_order": next_order},
    )


# ---------------------------------------------------------------------------
# 원료 관리 — 기능성 원료(Ingredient) 목록/추가/삭제
# 효과·부작용(JSON) 등 상세 편집은 상세 모달(별도 태스크)에서 담당한다.
# ---------------------------------------------------------------------------
def _get_ingredient(request):
    """POST 의 id 로 Ingredient 를 찾고, 없으면 메시지를 남기고 None 반환."""
    try:
        return Ingredient.objects.get(id=request.POST.get("id", ""))
    except (Ingredient.DoesNotExist, ValueError):
        messages.error(request, "성분을 찾을 수 없습니다.")
        return None


def _recommended_length_error(min_recommended, max_recommended):
    """minRecommended/maxRecommended 는 CharField(max_length=50) 이므로,
    폼에서 이를 초과해 POST 되면 저장 시 Postgres DataError(500)가 발생한다.
    모델 필드의 max_length 를 기준으로 미리 검증해 오류 메시지를 돌려준다
    (문제 없으면 None).
    """
    fields = {
        "최소권장량": (min_recommended, "minRecommended"),
        "최대권장량": (max_recommended, "maxRecommended"),
    }
    for label, (value, field_name) in fields.items():
        max_length = Ingredient._meta.get_field(field_name).max_length
        if value and len(value) > max_length:
            return f"{label}은 {max_length}자를 초과할 수 없습니다."
    return None


def _parse_json_list(raw):
    """폼에서 온 JSON 문자열을 '비어있지 않은 문자열' 리스트로 정규화한다.

    상세 모달의 리스트 편집 UI(효과/부작용/핵심 포인트/출처)가 항목들을
    JSON 배열 문자열로 담아 보낸다. 파싱 실패나 리스트가 아니면 빈 리스트를 반환한다.
    """
    try:
        data = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()]


def ingredient_list(request):
    """원료 · 기능성 원료(Ingredient) 관리 — 목록/추가/삭제.

    이름/주성분/권장량 등 기본 필드만 다룬다(효과·부작용 상세는 상세 모달 태스크).
    ProductIngredient.ingredient 는 PROTECT 이므로, 제품이 사용 중인 성분은
    삭제하지 않고 사용 중인 제품 수를 안내한다(기존 admin 은 연결을 강제 삭제했으나
    /admin/home 에서는 실수 삭제를 막기 위해 방지·안내로 바꾼다).
    """
    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "create":
            name = request.POST.get("name", "").strip()
            min_recommended = request.POST.get("minRecommended", "").strip()
            max_recommended = request.POST.get("maxRecommended", "").strip()
            length_error = _recommended_length_error(min_recommended, max_recommended)
            if not name:
                messages.error(request, "성분 이름을 입력해주세요.")
            elif length_error:
                messages.error(request, length_error)
            else:
                Ingredient.objects.create(
                    name=name,
                    mainIngredient=request.POST.get("mainIngredient", "").strip()
                    or None,
                    minRecommended=min_recommended or None,
                    maxRecommended=max_recommended or None,
                )
                messages.success(request, f'"{name}" 성분이 추가되었습니다.')
            return redirect("admin_home_ingredient")

        if action == "update":
            # 상세 모달 저장 — 기본 필드 + 효과/부작용(JSON) + 성분 가이드(1:1).
            ingredient = _get_ingredient(request)
            if ingredient is None:
                return redirect("admin_home_ingredient")
            name = request.POST.get("name", "").strip()
            min_recommended = request.POST.get("minRecommended", "").strip()
            max_recommended = request.POST.get("maxRecommended", "").strip()
            if not name:
                messages.error(request, "성분 이름을 입력해주세요.")
                return redirect("admin_home_ingredient")
            length_error = _recommended_length_error(min_recommended, max_recommended)
            if length_error:
                messages.error(request, length_error)
                return redirect("admin_home_ingredient")
            with transaction.atomic():
                ingredient.name = name
                ingredient.mainIngredient = (
                    request.POST.get("mainIngredient", "").strip() or None
                )
                ingredient.minRecommended = min_recommended or None
                ingredient.maxRecommended = max_recommended or None
                ingredient.effect = _parse_json_list(request.POST.get("effect"))
                ingredient.sideEffect = _parse_json_list(request.POST.get("sideEffect"))
                ingredient.save()
                # 성분 가이드(IngredientGuide, 1:1) — 없으면 만들고 있으면 갱신한다.
                guide, _ = IngredientGuide.objects.get_or_create(ingredient=ingredient)
                guide.keyPoints = _parse_json_list(request.POST.get("keyPoints"))
                guide.sources = _parse_json_list(request.POST.get("sources"))
                guide.save()
            messages.success(request, f'"{name}" 성분 정보가 저장되었습니다.')
            return redirect("admin_home_ingredient")

        if action == "delete":
            ingredient = _get_ingredient(request)
            if ingredient is None:
                return redirect("admin_home_ingredient")
            used = ingredient.productIngredients.count()
            if used:
                # PROTECT — 제품이 사용 중이면 삭제를 막고 사용처를 안내한다.
                messages.error(
                    request,
                    f'"{ingredient.name}" 성분은 제품 {used}개에서 사용 중이라 '
                    "삭제할 수 없습니다. 먼저 해당 제품에서 성분 연결을 해제해주세요.",
                )
            else:
                name = ingredient.name
                try:
                    ingredient.delete()
                    messages.success(request, f'"{name}" 성분이 삭제되었습니다.')
                except ProtectedError:
                    # count() 확인 이후 경합으로 연결이 생긴 경우의 2차 방어
                    messages.error(
                        request,
                        f'"{name}" 성분은 사용 중이라 삭제할 수 없습니다.',
                    )
            return redirect("admin_home_ingredient")

        messages.error(request, "알 수 없는 요청입니다.")
        return redirect("admin_home_ingredient")

    ingredients = (
        Ingredient.objects.select_related("guide")
        .annotate(product_count=Count("productIngredients", distinct=True))
        .order_by("id")
    )
    return _ah_render(
        request,
        "admin_home/ingredient_list.html",
        {"ingredients": ingredients},
    )


def _get_other_ingredient(request):
    """POST 의 id 로 OtherIngredient 를 찾고, 없으면 메시지를 남기고 None 반환."""
    try:
        return OtherIngredient.objects.get(id=request.POST.get("id", ""))
    except (OtherIngredient.DoesNotExist, ValueError):
        messages.error(request, "기타 원료를 찾을 수 없습니다.")
        return None


def ingredient_other(request):
    """원료 · 기타 원료(OtherIngredient) 관리 — 목록/추가/수정/삭제.

    이름(name) 한 필드만 갖는 단순 모델이라 별도 상세 모달 없이 인라인 수정 폼을 쓴다.
    name 은 unique 제약이라 생성/수정 시 중복 이름을 막고 안내한다.
    ProductOtherIngredient.other_ingredient 는 PROTECT 이므로, 제품이 사용 중인
    기타 원료는 삭제하지 않고 사용 중인 제품 수를 안내한다.
    """
    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "create":
            name = request.POST.get("name", "").strip()
            if not name:
                messages.error(request, "기타 원료 이름을 입력해주세요.")
            elif OtherIngredient.objects.filter(name=name).exists():
                messages.error(request, f'"{name}" 기타 원료가 이미 존재합니다.')
            else:
                OtherIngredient.objects.create(name=name)
                messages.success(request, f'"{name}" 기타 원료가 추가되었습니다.')
            return redirect("admin_home_ingredient_other")

        if action == "update":
            other = _get_other_ingredient(request)
            if other is None:
                return redirect("admin_home_ingredient_other")
            name = request.POST.get("name", "").strip()
            if not name:
                messages.error(request, "기타 원료 이름을 입력해주세요.")
            elif (
                OtherIngredient.objects.filter(name=name)
                .exclude(id=other.id)
                .exists()
            ):
                messages.error(request, f'"{name}" 기타 원료가 이미 존재합니다.')
            else:
                other.name = name
                other.save()
                messages.success(request, f'"{name}" 기타 원료가 수정되었습니다.')
            return redirect("admin_home_ingredient_other")

        if action == "delete":
            other = _get_other_ingredient(request)
            if other is None:
                return redirect("admin_home_ingredient_other")
            used = other.products.count()
            if used:
                # PROTECT — 제품이 사용 중이면 삭제를 막고 사용처를 안내한다.
                messages.error(
                    request,
                    f'"{other.name}" 기타 원료는 제품 {used}개에서 사용 중이라 '
                    "삭제할 수 없습니다. 먼저 해당 제품에서 연결을 해제해주세요.",
                )
            else:
                name = other.name
                try:
                    other.delete()
                    messages.success(request, f'"{name}" 기타 원료가 삭제되었습니다.')
                except ProtectedError:
                    # count() 확인 이후 경합으로 연결이 생긴 경우의 2차 방어
                    messages.error(
                        request,
                        f'"{name}" 기타 원료는 사용 중이라 삭제할 수 없습니다.',
                    )
            return redirect("admin_home_ingredient_other")

        messages.error(request, "알 수 없는 요청입니다.")
        return redirect("admin_home_ingredient_other")

    others = OtherIngredient.objects.annotate(
        product_count=Count("products", distinct=True),
    ).order_by("name")
    return _ah_render(
        request,
        "admin_home/ingredient_other.html",
        {"others": others},
    )
