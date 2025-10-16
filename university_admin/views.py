from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from .models import AdminProfile
from students.models import Student, Admin, University, Candidate, Election
from .serializers import AdminProfileSerializer, StudentSerializer, CandidateSerializer, ElectionSerializer
import csv
from io import TextIOWrapper
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        """Handle admin login with email and password, returning JWT tokens."""
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            student = Student.objects.get(email=email)
            admin, created_admin = Admin.objects.get_or_create(student=student, defaults={'role': 'admin'})
            if created_admin:
                logger.info(f"Created Admin for student {student.id}")
            if not student.check_password(password):
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            admin_profile, created_profile = AdminProfile.objects.get_or_create(
                admin=admin, defaults={'university': student.university}
            )
            if created_profile:
                logger.info(f"Created AdminProfile for admin {admin.student.student_id}")
            refresh = RefreshToken.for_user(student)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            return Response({
                "message": "Login successful",
                "admin": {"email": admin.student.email, "name": admin.student.name},
                "status": True,
                "access_token": access_token,
                "refresh_token": refresh_token
            }, status=status.HTTP_200_OK)
        except (Student.DoesNotExist, Admin.DoesNotExist):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return Response({"error": f"Login failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        """Refresh JWT access token using a refresh token."""
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({
                "access_token": access_token,
                "message": "Token refreshed successfully"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return Response({
                "error": "Invalid or expired refresh token",
                "detail": str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)

class ImportStudentsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        """Import students from a CSV file for the admin's university."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_authenticated:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({"error": "No CSV file provided"}, status=status.HTTP_400_BAD_REQUEST)
        if not csv_file.name.endswith('.csv'):
            return Response({"error": "File must be a CSV"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            file_wrapper = TextIOWrapper(csv_file, encoding='utf-8')
            csv_data = csv.DictReader(file_wrapper)
            for row in csv_data:
                university_id = row.get('university_id')
                if not university_id or int(university_id) != admin_profile.university.id:
                    continue
                try:
                    university = get_object_or_404(University, id=int(university_id))
                except (ValueError, TypeError):
                    return Response({"error": f"Invalid university ID for student {row.get('student_id')}"},
                                  status=status.HTTP_400_BAD_REQUEST)
                Student.objects.update_or_create(
                    student_id=row['student_id'],
                    defaults={
                        'name': row['name'],
                        'email': row['email'],
                        'phone_number': row['phone_number'],
                        'university': university,
                        'can_vote': True
                    }
                )
            logger.info(f"Imported students for university {admin_profile.university.id}")
            return Response({"message": "Students imported successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            return Response({"error": f"Error processing CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class AdminListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """List all admins for the authenticated admin's university."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        admins = Admin.objects.filter(student__university=admin_profile.university)
        serializer = AdminProfileSerializer([{'admin': admin, 'university': admin_profile.university} for admin in admins], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class StudentAddView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        """Add a new student to the database."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StudentSerializer(data=request.data)
        if serializer.is_valid():
            student = serializer.save(university=admin_profile.university)
            logger.info(f"Added new student with student_id {student.student_id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, student_id):
        """Update an existing student's details."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        student = get_object_or_404(Student, student_id=student_id)
        if student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = StudentSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Updated student with student_id {student_id}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, student_id):
        """Delete a student from the database."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        student = get_object_or_404(Student, student_id=student_id)
        if student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        student.delete()
        logger.info(f"Deleted student with student_id {student_id}")
        return Response({"message": "Student deleted"}, status=status.HTTP_200_OK)

class CandidateCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        """Create a new candidate from a student."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        student_id = request.data.get('student_id')
        student = get_object_or_404(Student, student_id=student_id)
        if student.university != admin_profile.university:
            return Response({"error": "Candidate must be from the same university"}, status=status.HTTP_403_FORBIDDEN)
        if Candidate.objects.filter(student=student).exists():
            return Response({"error": "Student is already a candidate"}, status=status.HTTP_400_BAD_REQUEST)
        candidate = Candidate.objects.create(student=student)
        serializer = CandidateSerializer(candidate)
        logger.info(f"Created candidate with student_id {student_id}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CandidateAssignPositionView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, student_id):
        """Assign a position to an existing candidate."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        candidate = get_object_or_404(Candidate, student__student_id=student_id)
        if candidate.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        position = request.data.get('position')
        if not position:
            return Response({"error": "Position is required"}, status=status.HTTP_400_BAD_REQUEST)
        candidate.position = position
        candidate.save()
        logger.info(f"Assigned position {position} to candidate with student_id {student_id}")
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CandidateListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """List all candidates for the authenticated admin's university."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        candidates = Candidate.objects.filter(student__university=admin_profile.university)
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CandidateUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, student_id):
        """Update an existing candidate's details."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        candidate = get_object_or_404(Candidate, student__student_id=student_id)
        if candidate.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CandidateSerializer(candidate, data=request.data, partial=True, context={'view': self, 'pk': candidate})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CandidateDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, student_id):
        """Delete a candidate."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        candidate = get_object_or_404(Candidate, student__student_id=student_id)
        if candidate.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        candidate.delete()
        logger.info(f"Deleted candidate with student_id {student_id}")
        return Response({"message": "Candidate deleted"}, status=status.HTTP_200_OK)

class ElectionCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        """Create a new election for the admin's university."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        data = request.data.copy()
        data['university'] = admin_profile.university.id  # Changed from 'admin_profile.university' to 'admin_profile.university.id'
        serializer = ElectionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Created election {data['name']}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ElectionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """List all elections for the authenticated admin's university."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        elections = Election.objects.filter(university=admin_profile.university)
        serializer = ElectionSerializer(elections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ElectionUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        """Update an existing election."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        election = get_object_or_404(Election, pk=pk)
        if election.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = ElectionSerializer(election, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ElectionDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        """Delete an election."""
        try:
            admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        except Exception:
            return Response({"error": "No AdminProfile found for the authenticated user. Please contact support."}, status=status.HTTP_404_NOT_FOUND)
        election = get_object_or_404(Election, pk=pk)
        if election.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        election.delete()
        logger.info(f"Deleted election with pk {pk}")
        return Response({"message": "Election deleted"}, status=status.HTTP_200_OK)