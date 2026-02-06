from django.urls import path
from socials.views import AppleSigninView, AdvertisementInquiryView, SocialPreLoginView, SocialTermsOfServiceView

urlpatterns = [
    path("prelogin/", SocialPreLoginView.as_view(), name= "social_prelogin"),
    path("apple/", AppleSigninView.as_view(), name="apple_signin"),
    path("advertisement/", AdvertisementInquiryView.as_view(), name="advertisement_inquiry"),
    path("terms/", SocialTermsOfServiceView.as_view(), name="terms_of_service"),
]