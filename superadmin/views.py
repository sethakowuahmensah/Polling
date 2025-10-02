from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SuperAdmin
from .serializers import SuperAdminSerializer

# For Google Authenticator (TOTP)
import pyotp


class SuperAdminLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        otp = request.data.get('otp')  # OTP field for 2FA

        if not email or not password:
            return Response({"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)

        admin = get_object_or_404(SuperAdmin, email=email)

        if not admin.check_password(password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # If OTP is provided, validate Google Authenticator TOTP
        if otp:
            if admin.two_fa_secret:
                totp = pyotp.TOTP(admin.two_fa_secret)
                if totp.verify(otp):
                    return Response({
                        "message": "Login successful with 2FA",
                        "admin": SuperAdminSerializer(admin).data
                    })
            return Response({"error": "Invalid 2FA code"}, status=status.HTTP_401_UNAUTHORIZED)

        # For Google Authenticator setup (if not exists)
        if not admin.two_fa_secret:
            admin.two_fa_secret = pyotp.random_base32()
            admin.save()

        return Response({
            "message": "Use Google Authenticator for 2FA.",
            "admin": SuperAdminSerializer(admin).data,
            "google_auth_secret": admin.two_fa_secret  # send secret for first-time setup
        })


# ✅ New endpoint to verify OTP separately
class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP are required"}, status=status.HTTP_400_BAD_REQUEST)

        admin = get_object_or_404(SuperAdmin, email=email)

        if not admin.two_fa_secret:
            return Response({"error": "2FA not set up for this account"}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(admin.two_fa_secret)
        if totp.verify(otp):
            return Response({
                "message": "OTP verified successfully",
                "admin": SuperAdminSerializer(admin).data,
                "status": True
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired OTP", "status": False}, status=status.HTTP_400_BAD_REQUEST)
