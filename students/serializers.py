from rest_framework import serializers
from .models import Student, Candidate, Vote

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = '__all__'

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = '__all__'

class StudentLoginSerializer(serializers.Serializer):
    student_id = serializers.CharField()

class OTPVerificationSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    otp = serializers.CharField()
    method = serializers.ChoiceField(choices=['email', 'phone'])
