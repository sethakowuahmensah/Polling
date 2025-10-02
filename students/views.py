from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import pyotp, qrcode, io, base64
from .models import Student, Candidate, Vote, University
from .serializers import StudentSerializer, CandidateSerializer, VoteSerializer, StudentLoginSerializer, OTPVerificationSerializer

class ImportStudentsView(APIView):
    """
    Import students via JSON for Postman testing
    """
    def post(self, request):
        students = request.data.get('students')
        if not students:
            return Response(
                {"error": "No student data provided. Send JSON like {'students': [...]}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        for row in students:
            university_id = row.get('university_id')
            if not university_id:
                return Response({"error": f"University ID missing for student {row.get('student_id')}"},
                                status=status.HTTP_400_BAD_REQUEST)
            university = get_object_or_404(University, id=university_id)

            Student.objects.update_or_create(
                student_id=row['student_id'],
                defaults={
                    'name': row['name'],
                    'email': row['email'],
                    'phone_number': row['phone_number'],
                    'university': university
                }
            )

        return Response({"message": "Students imported successfully"}, status=status.HTTP_200_OK)


class StudentLoginView(APIView):
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data['student_id']
        student = get_object_or_404(Student, student_id=student_id)
        totp_uri = student.get_totp_uri()

        # Generate QR code for Google Authenticator
        qr = qrcode.make(totp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()  # base64 to send via JSON

        return Response({
            "message": "Login with Google Authenticator",
            "qr_code_base64": qr_base64
        })


class OTPGenerateView(APIView):
    def post(self, request):
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({"error": "student_id required"}, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, student_id=student_id)

        # Generate OTP via Google Authenticator
        totp = pyotp.TOTP(student.otp_secret)
        otp = totp.now()

        # Normally, frontend reads the OTP from Authenticator app
        return Response({"message": "Use Google Authenticator to get your OTP"})


class OTPVerifyView(APIView):
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


class CastVoteView(APIView):
    def post(self, request):
        student_id = request.data.get('student_id')
        candidate_id = request.data.get('candidate_id')
        if not student_id or not candidate_id:
            return Response({"error": "student_id and candidate_id required"}, status=status.HTTP_400_BAD_REQUEST)

        student = get_object_or_404(Student, student_id=student_id, is_authenticated=True)
        candidate = get_object_or_404(Candidate, id=candidate_id)

        if Vote.objects.filter(student=student, candidate__position=candidate.position).exists():
            return Response({"error": "You have already voted for this position"}, status=status.HTTP_400_BAD_REQUEST)

        Vote.objects.create(student=student, candidate=candidate)
        return Response({"message": "Vote cast successfully"})
