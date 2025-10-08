from rest_framework import serializers
from .models import Student, University, Admin
from django.contrib.auth.hashers import make_password

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name']

class StudentSignupSerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=20)

class StudentLoginSerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=20)
    password = serializers.CharField(max_length=128, write_only=True)
    method = serializers.ChoiceField(choices=['email', 'google'])

class OTPVerifySerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6)
    method = serializers.ChoiceField(choices=['email', 'google'])

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(max_length=128)  # Only new_password is required in the body

class StudentSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all(), allow_null=True)
    class Meta:
        model = Student
        fields = [
            'student_id', 'name', 'email', 'phone_number', 'university',
            'is_active', 'is_staff', 'can_vote', 'date_joined', 'password'
        ]
        read_only_fields = ['is_active', 'is_staff', 'can_vote', 'date_joined']
        extra_kwargs = {'password': {'write_only': True, 'required': False}}
    def validate_university(self, value):
        if value is None:
            return value
        if not University.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Invalid university ID.")
        return value
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        student = Student(**validated_data)
        if password:
            student.set_password(password)
        else:
            student.set_unusable_password()
        student.save()
        return student
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class AdminSerializer(serializers.ModelSerializer):
    student = StudentSerializer()
    class Meta:
        model = Admin
        fields = ['student', 'role', 'name']
        read_only_fields = ['role']
    def create(self, validated_data):
        student_data = validated_data.pop('student')
        # create Student via serializer to hash password appropriately
        student_serializer = StudentSerializer(data=student_data)
        student_serializer.is_valid(raise_exception=True)
        student = student_serializer.save()
        admin = Admin.objects.create(student=student, **validated_data)
        return admin
    def update(self, instance, validated_data):
        student_data = validated_data.pop('student', None)
        if student_data:
            student_serializer = StudentSerializer(instance=instance.student, data=student_data, partial=True)
            student_serializer.is_valid(raise_exception=True)
            student_serializer.save()
        instance.name = validated_data.get('name', instance.name)
        instance.role = validated_data.get('role', instance.role)
        instance.save()
        return instance