from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, SignupView, VerifyEmailView, LoginView, OTPVerifyView, PasswordResetRequestView, PasswordResetConfirmView, StudentLoginView, OTPGenerateView, OTPVerifyView

router = DefaultRouter()
router.register(r'students', StudentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-email/<uidb64>/<token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', OTPVerifyView.as_view(), name='verify-otp'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('authenticator/', StudentLoginView.as_view(), name='authenticator-setup'),
    path('otp/generate/', OTPGenerateView.as_view(), name='otp-generate'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp-verify'),
]