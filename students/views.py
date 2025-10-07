from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import pyotp, qrcode, io, base64
from .models import Student, University
from .serializers import StudentSerializer, StudentLoginSerializer, OTPVerificationSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

class StudentLoginView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data['student_id']
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
    permission_classes = []
    def post(self, request):
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(Student, student_id=student_id)
        totp = pyotp.TOTP(student.otp_secret)
        otp = totp.now()
        return Response({"message": "Use Google Authenticator to get your OTP"})

class OTPVerifyView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = get_object_or_404(Student, student_id=serializer.validated_data['student_id'])
        otp = serializer.validated_data['otp']
        totp = pyotp.TOTP(student.otp_secret)
        if totp.verify(otp):
            student.is_authenticated = True
            student.save()
            return Response({"message": "OTP verified successfully"})
        return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)