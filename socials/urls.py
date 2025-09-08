from django.urls import path
from socials.views import AppleSigninView


urlpatterns = [
    path("apple/", AppleSigninView.as_view(), name="apple_signin"),
]