from django.urls import path
from .views import BannerListView, apple_app_site_association, assetlinks

urlpatterns = [
    path('', BannerListView.as_view()),
    path('.well-known/apple-app-site-association', apple_app_site_association),
    path('.well-known/assetlinks.json', assetlinks),
]