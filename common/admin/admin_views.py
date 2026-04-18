from django.shortcuts import render, redirect, get_object_or_404
from common.models import Banner
from common.utils import upload_banner_to_s3

def banner_list_view(request):
    if request.method == "POST":
        image = request.FILES.get("image")
        order = request.POST.get("order", 0)
        if image:
            url = upload_banner_to_s3(image)
            Banner.objects.create(image_url=url, order=order)
        return redirect("admin_banner_list")

    banners = Banner.objects.all().order_by("order")
    return render(request, "common/admin_banner.html", {"banners": banners})

def banner_delete_view(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    banner.delete()
    return redirect("admin_banner_list")