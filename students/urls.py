from django.urls import path
from .views import StudentLoginView, OTPGenerateView, OTPVerifyView

urlpatterns = [
    path('login/', StudentLoginView.as_view(), name='student-login'),
    path('generate-otp/', OTPGenerateView.as_view(), name='generate-otp'),
    path('verify-otp/', OTPVerifyView.as_view(), name='verify-otp'),
]