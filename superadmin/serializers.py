from rest_framework import serializers
from .models import SuperAdmin
from students.models import University, Student, Candidate, Election

class SuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = ['id', 'name', 'email', 'phone_number', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        admin = SuperAdmin(**validated_data)
        admin.set_password(password)
        admin.save()
        return admin

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name']

class CandidateSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    class Meta:
        model = Candidate
        fields = ['student', 'nomination_date', 'is_active']
        read_only_fields = ['nomination_date']

class ElectionSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())
    class Meta:
        model = Election
        fields = ['name', 'university', 'start_date', 'end_date', 'is_active']

class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[("student", "student"), ("admin", "admin")])