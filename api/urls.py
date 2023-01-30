from django.urls import include, path
from rest_framework import routers
from api.views import *

router = routers.DefaultRouter()
router.register(r"auth", AuthenticateView, basename="auth")
router.register(r"accounts", AccountViewSet, basename="accounts")
router.register(r"verifications", VerificationViewSet, basename="verifications")
router.register(r"posts", PostViewSet, basename="posts")
router.register(r"notifications", NotificationViewSet, basename="notifications")


urlpatterns = [
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("search/", SearchViewSet.as_view(), name="search"),
]
