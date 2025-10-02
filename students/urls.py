from django.urls import path
from .views import ImportStudentsView, StudentLoginView, OTPGenerateView, OTPVerifyView, CastVoteView

urlpatterns = [
    path('import-students/', ImportStudentsView.as_view(), name='import-students'),
    path('login/', StudentLoginView.as_view(), name='student-login'),
    path('generate-otp/', OTPGenerateView.as_view(), name='generate-otp'),
    path('verify-otp/', OTPVerifyView.as_view(), name='verify-otp'),
    path('cast-vote/', CastVoteView.as_view(), name='cast-vote'),
]
