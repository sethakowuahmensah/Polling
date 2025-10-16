from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
import random, string
import pyotp, qrcode, io, base64
from django.contrib.auth.hashers import make_password
from django.conf import settings
from .models import Student, University
from .serializers import (
    StudentSerializer, StudentSignupSerializer, StudentLoginSerializer,
    OTPVerifySerializer, PasswordResetSerializer, PasswordResetConfirmSerializer
)
from io import StringIO
import csv

class StudentImportView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=403)
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"error": "No file provided"}, status=400)
        csv_data = StringIO(csv_file.read().decode('utf-8'))
        reader = csv.DictReader(csv_data)
        for row in reader:
            university, _ = University.objects.get_or_create(name=row.get('university', 'Default University'))
            Student.objects.update_or_create(
                student_id=row['student_id'],
                defaults={
                    'name': row.get('name', ''),
                    'email': row.get('email', ''),
                    'phone_number': row.get('phone_number', ''),
                    'university': university
                }
            )
        return Response({"message": "Students imported successfully"}, status=200)

class SignupView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = StudentSignupSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            try:
                student = Student.objects.get(student_id=student_id)
                # Check if student is already verified
                print(f"Debug: is_verified for {student_id} is {student.is_verified}")
                if student.is_verified:
                    return Response({"error": "Already signed up"}, status=status.HTTP_400_BAD_REQUEST)
                email = student.email
                token_generator = PasswordResetTokenGenerator()
                token = token_generator.make_token(student)
                uid = urlsafe_base64_encode(force_bytes(student.pk))
                current_site = get_current_site(request)
                verification_link = f"http://{current_site.domain}{reverse('verify-email', args=[uid, token])}"
                send_mail(
                    'Verify Your Email',
                    f'Click the link to verify your email: {verification_link}',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
                return Response({"message": "Verification email sent"}, status=status.HTTP_200_OK)
            except Student.DoesNotExist:
                return Response({"error": "Invalid student_id"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            student = Student.objects.get(pk=uid)
            token_generator = PasswordResetTokenGenerator()
            if token_generator.check_token(student, token):
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                student.set_password(temp_password)
                student.is_verified = True  # Set verified after successful verification
                student.save()
                send_mail(
                    'Temporary Password',
                    f'Your temporary password is: {temp_password}. Use it to login and reset your password.',
                    settings.EMAIL_HOST_USER,
                    [student.email],
                    fail_silently=False,
                )
                return Response({"message": "Email verified, temporary password sent"}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, Student.DoesNotExist):
            return Response({"error": "Invalid verification link"}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data['student_id']
        password = serializer.validated_data['password']
        method = serializer.validated_data['method']
        try:
            student = Student.objects.get(student_id=student_id)
            if student.check_password(password):
                if method == 'email':
                    otp = ''.join(random.choices('0123456789', k=6))
                    student.otp_temp = otp
                    student.otp_expiry_temp = timezone.now() + timedelta(minutes=5)
                    student.save()
                    print(f"Debug: OTP set to {otp}, Expiry set to {student.otp_expiry_temp}")
                    # Post-save check
                    student_refreshed = Student.objects.get(student_id=student_id)
                    print(f"Debug: After save - OTP: {student_refreshed.otp_temp}, Expiry: {student_refreshed.otp_expiry_temp}")
                    send_mail(
                        'OTP for Login',
                        f'Your OTP is: {otp}. It expires in 5 minutes.',
                        settings.EMAIL_HOST_USER,
                        [student.email],
                        fail_silently=False,
                    )
                    return Response({"message": "OTP sent to email", "method": "email"}, status=status.HTTP_200_OK)
                elif method == 'google':
                    return Response({"message": "Use Google Authenticator for OTP", "method": "google"}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid method"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:
            return Response({"error": "Invalid student_id"}, status=status.HTTP_400_BAD_REQUEST)

class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data['student_id']
        otp = serializer.validated_data['otp']
        method = serializer.validated_data['method']
        try:
            student = Student.objects.get(student_id=student_id)
            if method == 'email':
                stored_otp = student.otp_temp
                expiry = student.otp_expiry_temp
                print(f"Debug: Stored OTP: {stored_otp}, Provided OTP: {otp}, Expiry: {expiry}, Now: {timezone.now()}")
                otp_ok = stored_otp == otp and expiry > timezone.now()
                if otp_ok:
                    student.is_active = True
                    student.otp_temp = None  # Clear after use
                    student.otp_expiry_temp = None
                    student.save()
                    refresh = RefreshToken.for_user(student)
                    return Response({
                        "message": "Login successful",
                        "access_token": str(refresh.access_token),
                        "refresh_token": str(refresh)
                    }, status=status.HTTP_200_OK)
                return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
            elif method == 'google':
                totp = pyotp.TOTP(student.otp_secret)
                if totp.verify(otp):
                    student.is_active = True
                    student.save()
                    refresh = RefreshToken.for_user(student)
                    return Response({
                        "message": "Login successful",
                        "access_token": str(refresh.access_token),
                        "refresh_token": str(refresh)
                    }, status=status.HTTP_200_OK)
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Invalid method"}, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:
            return Response({"error": "Invalid student_id"}, status=status.HTTP_400_REQUEST)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            student = Student.objects.get(email=email)
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(student)
            uid = urlsafe_base64_encode(force_bytes(student.pk))
            current_site = get_current_site(request)
            reset_link = f"http://{current_site.domain}{reverse('password-reset-confirm', args=[uid, token])}"
            send_mail(
                'Password Reset Request',
                f'Click the link to reset your password: {reset_link}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)
        except Student.DoesNotExist:
            return Response({"error": "Invalid email"}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, uidb64, token):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data['new_password']
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            student = Student.objects.get(pk=uid)
            token_generator = PasswordResetTokenGenerator()
            if token_generator.check_token(student, token):
                student.set_password(new_password)
                student.save()
                return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, Student.DoesNotExist):
            return Response({"error": "Invalid reset link"}, status=status.HTTP_400_BAD_REQUEST)

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    def create(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not isinstance(request.user, User) or not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

class StudentLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        student_id = request.data.get('student_id')
        student = get_object_or_404(Student, student_id=student_id)
        totp_uri = student.get_totp_uri()
        qr = qrcode.make(totp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        return Response({
            "message": "Login with Google Authenticator",
            "qr_code_base64": qr_base64
        })

class OTPGenerateView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(Student, student_id=student_id)
        totp = pyotp.TOTP(student.otp_secret)
        _ = totp.now()  # don't return the OTP here
        return Response({"message": "Use Google Authenticator to get your OTP"})

class OTPVerificationView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data['student_id']
        otp = serializer.validated_data['otp']
        totp = pyotp.TOTP(student.otp_secret)
        if totp.verify(otp):
            student = get_object_or_404(Student, student_id=student_id)
            student.is_active = True
            student.save()
            return Response({"message": "OTP verified successfully"})
        return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)