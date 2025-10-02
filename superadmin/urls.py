from django.urls import path
from .views import (
    SuperAdminLoginView,
    VerifyOTPView,
    Disable2FAView,
    BulkUserImportView,
    RoleUpdateView
)

urlpatterns = [
    # Authentication endpoints
    path('login/', SuperAdminLoginView.as_view(), name='superadmin-login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('disable-2fa/', Disable2FAView.as_view(), name='disable-2fa'),

    # Bulk import for Admins + Students
    path('bulk-import/', BulkUserImportView.as_view(), name='bulk-import'),

    # Update role (SuperAdmin only)
    path('update-role/<int:pk>/', RoleUpdateView.as_view(), name='update-role'),
]