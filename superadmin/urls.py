from django.urls import path
from .views import SuperAdminLoginView, VerifyOTPView

urlpatterns = [
    path('login/', SuperAdminLoginView.as_view(), name='superadmin-login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
]
