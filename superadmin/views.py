from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from .models import SuperAdmin
from students.models import Student, Admin, University, Candidate, Election
from .serializers import SuperAdminSerializer, UniversitySerializer, CandidateSerializer, ElectionSerializer, RoleUpdateSerializer
from students.serializers import StudentSerializer, AdminSerializer
import csv
from io import TextIOWrapper

class SuperAdminLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            admin = SuperAdmin.objects.get(email=email)
        except SuperAdmin.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if not admin.check_password(password):
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(admin)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        return Response({
            "message": "Login successful",
            "admin": {"email": admin.email, "name": admin.name},
            "status": True,
            "access_token": access_token,
            "refresh_token": refresh_token
        }, status=status.HTTP_200_OK)

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
        if not request.user.is_superuser:
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
                if not university_id:
                    return Response({"error": f"University ID missing for student {row.get('student_id')}"},
                                  status=status.HTTP_400_BAD_REQUEST)
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
                        'university': university,
                        'can_vote': True
                    }
                )
            return Response({"message": "Students imported successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Error processing CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class AdminCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        required_fields = ['student_id', 'name', 'email', 'phone_number', 'university']
        missing = [field for field in required_fields if field not in request.data]
        if missing:
            return Response({"error": f"Missing required fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate university ID
        university_id = request.data.get('university')
        try:
            university_id = int(university_id)
            get_object_or_404(University, id=university_id)
        except (ValueError, TypeError):
            return Response({"error": "University must be a valid ID (integer)"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Construct student data
        student_data = {
            'student_id': request.data['student_id'],
            'name': request.data['name'],
            'email': request.data['email'],
            'phone_number': request.data['phone_number'],
            'university': university_id,
            'can_vote': True
        }
        
        # Use StudentSerializer directly to avoid nesting issues
        student_serializer = StudentSerializer(data=student_data)
        if student_serializer.is_valid():
            student = student_serializer.save()
            admin_data = {
                'student': student,
                'role': 'admin',
                'name': request.data.get('name', '')
            }
            admin = Admin.objects.create(**admin_data)
            return Response({
                "message": "Admin created",
                "admin": AdminSerializer(admin).data
            }, status=status.HTTP_201_CREATED)
        return Response(student_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        admins = Admin.objects.all()
        serializer = AdminSerializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdminUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, student_id):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        admin = get_object_or_404(Admin, student__student_id=student_id)
        student = admin.student
        university_id = request.data.get('university', student.university_id)
        try:
            university_id = int(university_id)
            get_object_or_404(University, id=university_id)
        except (ValueError, TypeError):
            return Response({"error": "University must be a valid ID (integer)"}, status=status.HTTP_400_BAD_REQUEST)
        student_data = {
            'name': request.data.get('name', student.name),
            'email': request.data.get('email', student.email),
            'phone_number': request.data.get('phone_number', student.phone_number),
            'university': university_id,
            'can_vote': True
        }
        student_serializer = StudentSerializer(student, data=student_data, partial=True)
        if student_serializer.is_valid():
            student_serializer.save()
            admin_data = {
                'role': request.data.get('role', admin.role),
                'name': request.data.get('name', admin.name)
            }
            for key, value in admin_data.items():
                setattr(admin, key, value)
            admin.save()
            return Response({
                "message": "Admin updated",
                "admin": AdminSerializer(admin).data
            }, status=status.HTTP_200_OK)
        return Response(student_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, student_id):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        admin = get_object_or_404(Admin, student__student_id=student_id)
        admin.delete()
        return Response({"message": "Admin deleted"}, status=status.HTTP_200_OK)

class UniversityCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = UniversitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UniversityListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        universities = University.objects.all()
        serializer = UniversitySerializer(universities, many=True)
        return Response(serializer.data)

class UniversityUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        university = get_object_or_404(University, pk=pk)
        serializer = UniversitySerializer(university, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UniversityDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        university = get_object_or_404(University, pk=pk)
        university.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class RoleUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, student_id):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = RoleUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        new_role = serializer.validated_data['role']
        admin_instance = Admin.objects.filter(student__student_id=student_id).first()
        if admin_instance:
            if new_role == "student":
                student = admin_instance.student
                admin_instance.delete()
                return Response({
                    "message": "Admin demoted to Student",
                    "user": StudentSerializer(student).data
                }, status=status.HTTP_200_OK)
            elif new_role == "admin":
                return Response({
                    "message": "Role unchanged (already an admin)",
                    "user": AdminSerializer(admin_instance).data
                }, status=status.HTTP_200_OK)
        else:
            student_instance = Student.objects.filter(student_id=student_id).first()
            if student_instance:
                if new_role == "admin":
                    admin_data = {
                        'student': student_instance,
                        'role': "admin",
                        'name': student_instance.name
                    }
                    admin = Admin.objects.create(**admin_data)
                    return Response({
                        "message": "Student promoted to Admin",
                        "user": AdminSerializer(admin).data
                    }, status=status.HTTP_200_OK)
                elif new_role == "student":
                    return Response({
                        "message": "Role unchanged (already a student)",
                        "user": StudentSerializer(student_instance).data
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "User not found",
                    "user": {
                        "name": "Unknown",
                        "email": "Unknown",
                        "role": new_role
                    }
                }, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

class CandidateCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        student_id = request.data.get('student_id')
        student = get_object_or_404(Student, student_id=student_id)
        if Candidate.objects.filter(student=student).exists():
            return Response({"error": "Student is already a candidate"}, status=status.HTTP_400_BAD_REQUEST)
        candidate = Candidate.objects.create(student=student)
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CandidateListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        candidates = Candidate.objects.all()
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CandidateUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        candidate = get_object_or_404(Candidate, pk=pk)
        serializer = CandidateSerializer(candidate, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CandidateDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        candidate = get_object_or_404(Candidate, pk=pk)
        candidate.delete()
        return Response({"message": "Candidate deleted"}, status=status.HTTP_200_OK)

class ElectionCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        serializer = ElectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ElectionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        elections = Election.objects.all()
        serializer = ElectionSerializer(elections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ElectionUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        election = get_object_or_404(Election, pk=pk)
        serializer = ElectionSerializer(election, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ElectionDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        election = get_object_or_404(Election, pk=pk)
        election.delete()
        return Response({"message": "Election deleted"}, status=status.HTTP_200_OK)