from rest_framework import serializers
from students.models import Student, Admin, University, Candidate, Election
from students.serializers import StudentSerializer

class SuperAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=100)

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name']

class CandidateSerializer(serializers.ModelSerializer):
    student = StudentSerializer()

    class Meta:
        model = Candidate
        fields = ['student', 'nomination_date', 'is_active']

class ElectionSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())

    class Meta:
        model = Election
        fields = ['id', 'name', 'university', 'start_date', 'end_date', 'is_active']

class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['student', 'admin'])

class AdminSerializer(serializers.ModelSerializer):
    student = StudentSerializer()

    class Meta:
        model = Admin
        fields = ['student', 'role', 'name']
        read_only_fields = ['role']

    def create(self, validated_data):
        student_data = validated_data.pop('student')
        student = Student.objects.create(**student_data)
        admin = Admin.objects.create(student=student, **validated_data)
        return admin

    def update(self, instance, validated_data):
        student_data = validated_data.pop('student', None)
        if student_data:
            student_serializer = StudentSerializer(instance.student, data=student_data, partial=True)
            if student_serializer.is_valid():
                student_serializer.save()
        instance.name = validated_data.get('name', instance.name)
        instance.role = validated_data.get('role', instance.role)
        instance.save()
        return instance