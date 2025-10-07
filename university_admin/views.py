from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from .models import AdminProfile
from students.models import Student, Admin as StudentAdmin, University, Candidate, Election
from .serializers import AdminProfileSerializer, StudentSerializer, CandidateSerializer, ElectionSerializer
import csv
from io import TextIOWrapper

class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            student = Student.objects.get(email=email)
            admin = StudentAdmin.objects.get(student=student)
            # Adjust password check based on Student model
            if not student.check_password(password):  # Assumes Student has set_password/check_password
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
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
        except (Student.DoesNotExist, StudentAdmin.DoesNotExist):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class AdminCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        required_fields = ['student_id', 'name', 'email', 'phone_number']
        missing = [field for field in required_fields if field not in request.data]
        if missing:
            return Response({"error": f"Missing required fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate university ID
        university_id = admin_profile.university.id
        get_object_or_404(University, id=university_id)
        
        student_data = {
            'student_id': request.data['student_id'],
            'name': request.data['name'],
            'email': request.data['email'],
            'phone_number': request.data['phone_number'],
            'university': university_id,
            'can_vote': True
        }
        student_serializer = StudentSerializer(data=student_data)
        if student_serializer.is_valid():
            student = student_serializer.save()
            admin = StudentAdmin.objects.create(student=student, role="admin")
            AdminProfile.objects.create(admin=admin, university=admin_profile.university)
            return Response({
                "message": "Admin created",
                "admin": AdminProfileSerializer({
                    'admin': admin,
                    'university': admin_profile.university
                }).data
            }, status=status.HTTP_201_CREATED)
        return Response(student_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
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

class ImportStudentsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
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
                    university_id = int(university_id)
                    university = get_object_or_404(University, id=university_id)
                except (ValueError, TypeError):
                    return Response({"error": f"Invalid university ID for student {row.get('student_id')}"},
                                  status=status.HTTP_400_BAD_REQUEST)
                Student.objects.update_or_create(
                    student_id=row['student_id'],
                    defaults={
                        'name': row['name'],
                        'email': row['email'],
                        'phone_number': row['phone_number'],
                        'university': university,  # Pass University instance
                        'can_vote': True
                    }
                )
            return Response({"message": "Students imported successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Error processing CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class AdminListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        admins = StudentAdmin.objects.filter(student__university=admin_profile.university)
        serializer = AdminProfileSerializer([{'admin': admin, 'university': admin_profile.university} for admin in admins], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdminUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        admin = get_object_or_404(StudentAdmin, pk=pk)
        if admin.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        student = admin.student
        student_data = {
            'name': request.data.get('name', student.name),
            'email': request.data.get('email', student.email),
            'phone_number': request.data.get('phone_number', student.phone_number),
            'university': admin_profile.university.id,
            'can_vote': True
        }
        serializer = StudentSerializer(student, data=student_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Admin updated",
                "admin": AdminProfileSerializer({
                    'admin': admin,
                    'university': admin_profile.university
                }).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        admin = get_object_or_404(StudentAdmin, pk=pk)
        if admin.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        student = admin.student
        admin.delete()
        student.delete()
        return Response({"message": "Admin deleted"}, status=status.HTTP_200_OK)

class CandidateCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        student_id = request.data.get('student_id')
        student = get_object_or_404(Student, student_id=student_id)
        if student.university != admin_profile.university:
            return Response({"error": "Candidate must be from the same university"}, status=status.HTTP_403_FORBIDDEN)
        if Candidate.objects.filter(student=student).exists():
            return Response({"error": "Student is already a candidate"}, status=status.HTTP_400_BAD_REQUEST)
        candidate = Candidate.objects.create(student=student)
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CandidateListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        candidates = Candidate.objects.filter(student__university=admin_profile.university)
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CandidateUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        candidate = get_object_or_404(Candidate, pk=pk)
        if candidate.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CandidateSerializer(candidate, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CandidateDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        candidate = get_object_or_404(Candidate, pk=pk)
        if candidate.student.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        candidate.delete()
        return Response({"message": "Candidate deleted"}, status=status.HTTP_200_OK)

class ElectionCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        data = request.data.copy()
        data['university'] = admin_profile.university.id
        serializer = ElectionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ElectionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        elections = Election.objects.filter(university=admin_profile.university)
        serializer = ElectionSerializer(elections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ElectionUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
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
        admin_profile = get_object_or_404(AdminProfile, admin__student__id=request.user.id)
        election = get_object_or_404(Election, pk=pk)
        if election.university != admin_profile.university:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        election.delete()
        return Response({"message": "Election deleted"}, status=status.HTTP_200_OK)