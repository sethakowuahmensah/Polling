from rest_framework import serializers
from students.models import Student, Admin as StudentAdmin, Candidate, Election
from .models import AdminProfile

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'student_id', 'name', 'email', 'phone_number', 'university', 'can_vote']

class AdminProfileSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source='admin.student.student_id', read_only=True)
    name = serializers.CharField(source='admin.student.name', read_only=True)
    email = serializers.CharField(source='admin.student.email', read_only=True)
    class Meta:
        model = AdminProfile
        fields = ['student_id', 'name', 'email', 'university']

class CandidateSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    name = serializers.CharField(source='student.name', read_only=True)
    class Meta:
        model = Candidate
        fields = ['student_id', 'name', 'nomination_date', 'is_active']

class ElectionSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source='university.name', read_only=True)
    class Meta:
        model = Election
        fields = ['id', 'name', 'university', 'university_name', 'start_date', 'end_date', 'is_active']