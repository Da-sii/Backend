from django.urls import path
from common.admin import admin_views

urlpatterns = [
    path("", admin_views.banner_list_view, name="admin_banner_list"),
    path("delete/<int:banner_id>/", admin_views.banner_delete_view, name="admin_banner_delete"),
]