from django.urls import path
from socials.views import AppleSigninView, AdvertisementInquiryView


urlpatterns = [
    path("apple/", AppleSigninView.as_view(), name="apple_signin"),
    path("advertisement/", AdvertisementInquiryView.as_view(), name="advertisement_inquiry"),
]