from rest_framework import serializers
from .models import Student, Admin, University

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name']

class StudentSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())
    class Meta:
        model = Student
        fields = ['student_id', 'name', 'email', 'phone_number', 'university', 'is_authenticated', 'can_vote']
        read_only_fields = ['is_authenticated', 'can_vote', 'otp_secret']

    def validate_university(self, value):
        if not University.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Invalid university ID.")
        return value

class AdminSerializer(serializers.ModelSerializer):
    student = StudentSerializer()
    admin_name = serializers.CharField(source='name', required=False)
    class Meta:
        model = Admin
        fields = ['student', 'role', 'admin_name']

    def create(self, validated_data):
        student_data = validated_data.pop('student')
        # Ensure university is an integer
        if isinstance(student_data['university'], University):
            student_data['university'] = student_data['university'].id
        student_serializer = StudentSerializer(data=student_data)
        if student_serializer.is_valid():
            student = student_serializer.save()
            validated_data['student'] = student
            validated_data['name'] = validated_data.get('name', student.name)
            return super().create(validated_data)
        raise serializers.ValidationError(student_serializer.errors)

    def update(self, instance, validated_data):
        student_data = validated_data.pop('student', None)
        if student_data:
            if isinstance(student_data['university'], University):
                student_data['university'] = student_data['university'].id
            student_serializer = StudentSerializer(instance.student, data=student_data, partial=True)
            if student_serializer.is_valid():
                student_serializer.save()
            else:
                raise serializers.ValidationError(student_serializer.errors)
        instance.name = validated_data.get('name', instance.name)
        instance.role = validated_data.get('role', instance.role)
        instance.save()
        return instance

class StudentLoginSerializer(serializers.Serializer):
    student_id = serializers.CharField()

class OTPVerificationSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    otp = serializers.CharField()
    method = serializers.ChoiceField(choices=['email', 'phone'])