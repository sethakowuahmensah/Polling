from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.core.mail import EmailMessage
from django.conf import settings
from .models import SuperAdmin, Admin, Student
from .serializers import SuperAdminSerializer, BulkUserSerializer, RoleUpdateSerializer
import pyotp
import qrcode
import io
import base64
import csv
import json
import pandas as pd
from io import TextIOWrapper
import os
import uuid


class SuperAdminLoginView(APIView):
    """
    Step 1: Initial login with email/password
    Returns QR code if 2FA not set up, or requires OTP if already set up
    """
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({
                "error": "Email and password required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin = SuperAdmin.objects.get(email=email)
        except SuperAdmin.DoesNotExist:
            return Response({
                "error": "Invalid credentials"
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Verify password
        if not admin.check_password(password):
            return Response({
                "error": "Invalid credentials"
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Check if 2FA is already enabled
        if admin.two_fa_enabled and admin.two_fa_secret:
            return Response({
                "message": "Please provide OTP from Google Authenticator",
                "requires_otp": True,
                "email": admin.email
            }, status=status.HTTP_200_OK)

        # First time login - generate 2FA secret and QR code
        if not admin.two_fa_secret:
            admin.generate_2fa_secret()
        
        # Generate QR code
        totp_uri = admin.get_totp_uri()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Send setup email with manual entry key
        try:
            email_body = f"""
Hello {admin.name},

You are setting up Two-Factor Authentication (2FA) for your account.

Please follow these steps:

OPTION 1 - Scan QR Code (Recommended):
1. Download Google Authenticator app on your phone (iOS/Android)
2. Open the app and tap the "+" button
3. Select "Scan a QR code"
4. Scan the QR code provided in the login response

OPTION 2 - Manual Entry:
If you cannot scan the QR code, manually enter this key in Google Authenticator:

Manual Entry Key: {admin.two_fa_secret}

Account Name: {admin.email}
Issuer: YourAppName

Steps for manual entry:
1. Open Google Authenticator app
2. Tap the "+" button
3. Select "Enter a setup key"
4. Enter the account name and the key above
5. Tap "Add"

After setup, enter the 6-digit code from the app to complete authentication.

IMPORTANT: Keep this key secure and do not share it with anyone.

Best regards,
YourAppName Security Team
            """
            
            email_msg = EmailMessage(
                subject="Two-Factor Authentication Setup - Manual Entry Key",
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[admin.email]
            )
            email_msg.send(fail_silently=False)
        except Exception as e:
            print(f"Email error: {str(e)}")
            # Continue even if email fails

        return Response({
            "message": "Scan QR code with Google Authenticator app",
            "requires_setup": True,
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "manual_entry_key": admin.two_fa_secret,  # Backup if QR scan fails
            "email": admin.email,
            "setup_instructions": "Scan the QR code or manually enter the key in Google Authenticator"
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    Step 2: Verify OTP code from Google Authenticator
    Used both for initial setup and subsequent logins
    """
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        is_setup = request.data.get("is_setup", False)  # True for first-time setup

        if not email or not otp:
            return Response({
                "error": "Email and OTP are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin = SuperAdmin.objects.get(email=email)
        except SuperAdmin.DoesNotExist:
            return Response({
                "error": "Invalid email"
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not admin.two_fa_secret:
            return Response({
                "error": "2FA not set up for this account"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify the OTP
        if admin.verify_totp(otp):
            # If this is initial setup, enable 2FA
            if is_setup and not admin.two_fa_enabled:
                admin.two_fa_enabled = True
                admin.save()
                
                return Response({
                    "message": "2FA setup completed successfully! You can now login.",
                    "admin": SuperAdminSerializer(admin).data,
                    "status": True,
                    "setup_complete": True
                }, status=status.HTTP_200_OK)
            
            # Regular login after 2FA is enabled
            # Generate JWT tokens
            refresh = RefreshToken.for_user(admin)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return Response({
                "message": "Login successful",
                "admin": SuperAdminSerializer(admin).data,
                "status": True,
                "access_token": access_token,
                "refresh_token": refresh_token
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "error": "Invalid or expired OTP",
                "status": False
            }, status=status.HTTP_400_BAD_REQUEST)


class Disable2FAView(APIView):
    """
    Allow SuperAdmin to disable 2FA (requires password confirmation)
    """
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({
                "error": "Email and password required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin = SuperAdmin.objects.get(email=email)
        except SuperAdmin.DoesNotExist:
            return Response({
                "error": "Invalid credentials"
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not admin.check_password(password):
            return Response({
                "error": "Invalid password"
            }, status=status.HTTP_401_UNAUTHORIZED)

        admin.two_fa_enabled = False
        admin.two_fa_secret = None
        admin.save()

        return Response({
            "message": "2FA disabled successfully"
        }, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    """
    Refresh access token using refresh token
    """
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        
        if not refresh_token:
            return Response({
                "error": "Refresh token required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            return Response({
                "access_token": access_token,
                "message": "Token refreshed successfully"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": "Invalid or expired refresh token",
                "detail": str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)


# ================= Bulk Import Users (Students/Admins) =================
class BulkUserImportView(APIView):
    permission_classes = [IsAuthenticated]  # Require authentication
    
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "File required"}, status=status.HTTP_400_BAD_REQUEST)

        filename = file.name.lower()
        extension = os.path.splitext(filename)[1]

        try:
            records = []

            if extension == ".csv":
                data = TextIOWrapper(file.file, encoding="utf-8")
                reader = csv.DictReader(data)
                records = list(reader)
            elif extension in [".xls", ".xlsx"]:
                df = pd.read_excel(file)
                records = df.to_dict(orient="records")
            elif extension == ".json":
                records = json.load(file)
            elif extension == ".txt":
                try:
                    records = json.load(file)
                except:
                    data = TextIOWrapper(file.file, encoding="utf-8")
                    reader = csv.DictReader(data, delimiter="\t")
                    records = list(reader)
            else:
                return Response({"error": f"Unsupported file type: {extension}"}, status=status.HTTP_400_BAD_REQUEST)

            imported_users = []
            errors = []

            for row in records:
                if row.get("role", "student") == "student":
                    if not row.get("student_id") or Student.objects.filter(student_id=row["student_id"]).exists():
                        errors.append({"row": row, "error": "Duplicate or missing student_id"})
                        continue
                    if Student.objects.filter(email=row.get("email")).exists():
                        errors.append({"row": row, "error": "Duplicate email"})
                        continue

                serializer = BulkUserSerializer(data=row)
                if serializer.is_valid():
                    serializer.save()
                    imported_users.append(serializer.data)
                else:
                    errors.append({"row": row, "error": serializer.errors})

            if errors:
                return Response({
                    "message": f"{len(imported_users)} users imported successfully, {len(errors)} rows skipped due to errors.",
                    "users": imported_users,
                    "errors": errors
                }, status=status.HTTP_207_MULTI_STATUS)

            return Response({
                "message": f"{len(imported_users)} users imported successfully.",
                "users": imported_users
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================= Role Update (SuperAdmin only) =================
class RoleUpdateView(APIView):
    def post(self, request, pk):
        user_instance = Student.objects.filter(pk=pk).first() or Admin.objects.filter(pk=pk).first()

        if not user_instance:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        serializer = RoleUpdateSerializer(data=request.data)
        if serializer.is_valid():
            new_role = serializer.validated_data["role"]

            if isinstance(user_instance, Student) and new_role == "admin":
                admin = Admin(
                    name=user_instance.name,
                    email=user_instance.email,
                    phone_number=user_instance.phone_number
                )
                admin.save()
                user_instance.delete()
                return Response({
                    "message": "Student promoted to Admin",
                    "user": {
                        "name": admin.name,
                        "email": admin.email,
                        "role": "admin"
                    }
                })

            elif isinstance(user_instance, Admin) and new_role == "student":
                student = Student(
                    student_id=str(uuid.uuid4()),
                    name=user_instance.name,
                    email=user_instance.email,
                    phone_number=user_instance.phone_number
                )
                student.save()
                user_instance.delete()
                return Response({
                    "message": "Admin demoted to Student",
                    "user": {
                        "name": student.name,
                        "email": student.email,
                        "role": "student"
                    }
                })

            return Response({
                "message": "Role unchanged",
                "user": {
                    "name": user_instance.name,
                    "email": user_instance.email,
                    "role": new_role
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)