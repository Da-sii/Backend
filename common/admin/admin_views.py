from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from common.models import Banner, BannerDetail
from common.utils import upload_banner_to_s3


def banner_list_view(request):
    error = None

    if request.method == "POST":
        image = request.FILES.get("image")
        order = request.POST.get("order", 1)

        if image:
            try:
                image_url = upload_banner_to_s3(image)
                Banner.objects.create(image_url=image_url, order=order)
                return redirect("admin_banner_list")
            except IntegrityError:
                error = f"순서 {order}은(는) 이미 사용 중입니다. 다른 순서를 입력해주세요."

    banners = Banner.objects.prefetch_related('details').all()
    return render(request, "common/admin_banner.html", {"banners": banners, "error": error})


def banner_delete_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    banner.delete()
    return redirect("admin_banner_list")


def banner_detail_add_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    error = None

    if request.method == "POST":
        detail_image = request.FILES.get("detail_image")
        order = request.POST.get("order", 1)

        if detail_image:
            try:
                detail_image_url = upload_banner_to_s3(detail_image)
                BannerDetail.objects.create(banner=banner, detail_image_url=detail_image_url, order=order)
                return redirect("admin_banner_list")
            except IntegrityError:
                error = f"배너 #{banner_id}에 순서 {order}은(는) 이미 사용 중입니다. 다른 순서를 입력해주세요."

    banners = Banner.objects.prefetch_related('details').all()
    return render(request, "common/admin_banner.html", {"banners": banners, "error": error, "error_banner_id": banner_id})


def banner_detail_delete_view(request, detail_id):
    detail = get_object_or_404(BannerDetail, id=detail_id)
    detail.delete()
    return redirect("admin_banner_list")
