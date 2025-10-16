from rest_framework import serializers
from students.models import Student, Admin, Candidate, Election, University  # Updated import, removed 'as StudentAdmin'
from .models import AdminProfile
import logging

# Set up logging
logger = logging.getLogger(__name__)

class StudentSerializer(serializers.ModelSerializer):
    """Serialize Student model data for admin operations."""
    class Meta:
        model = Student
        fields = ['id', 'student_id', 'name', 'email', 'phone_number', 'university', 'can_vote']
        extra_kwargs = {
            'id': {'read_only': True},
            'university': {'required': True},  # Ensure university is provided
        }

    def validate_university(self, value):
        """Validate that the university exists."""
        if not value or not University.objects.filter(id=value.id).exists():
            logger.warning(f"Invalid university ID provided: {value}")
            raise serializers.ValidationError("Invalid university ID. Please ensure the university exists.")
        return value

class AdminProfileSerializer(serializers.ModelSerializer):
    """Serialize AdminProfile data, including derived student details."""
    student_id = serializers.CharField(source='admin.student.student_id', read_only=True)
    name = serializers.CharField(source='admin.student.name', read_only=True)
    email = serializers.CharField(source='admin.student.email', read_only=True)
    role = serializers.CharField(source='admin.role', read_only=True)

    class Meta:
        model = AdminProfile
        fields = ['student_id', 'name', 'email', 'role', 'university']
        extra_kwargs = {
            'university': {'read_only': True},  # University is set via AdminProfile creation
        }

class CandidateSerializer(serializers.ModelSerializer):
    """Serialize Candidate model data with derived student details."""
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = Candidate
        fields = ['student_id', 'name', 'nomination_date', 'is_active']
        extra_kwargs = {
            'nomination_date': {'read_only': True},  # Set automatically on creation
            'is_active': {'default': True},  # Default to active unless updated
        }

    def validate(self, data):
        """Ensure candidate uniqueness and university match (handled in view)."""
        if 'student' in self.context.get('view').kwargs:
            candidate = self.context['view'].kwargs['pk']
            if Candidate.objects.filter(student=candidate.student).exclude(pk=candidate.pk).exists():
                logger.warning(f"Duplicate candidate attempt for student {candidate.student.student_id}")
                raise serializers.ValidationError("Student is already a candidate.")
        return data

class ElectionSerializer(serializers.ModelSerializer):
    """Serialize Election model data with derived university name."""
    university_name = serializers.CharField(source='university.name', read_only=True)

    class Meta:
        model = Election
        fields = ['id', 'name', 'university', 'university_name', 'start_date', 'end_date', 'is_active']  # Changed 'university_id' to 'university'
        extra_kwargs = {
            'id': {'read_only': True},
            'university': {},  # Make university writable
            'university_name': {'read_only': True},
        }

    def validate(self, data):
        """Validate election dates."""
        if 'start_date' in data and 'end_date' in data:
            if data['start_date'] >= data['end_date']:
                logger.warning(f"Invalid election dates: start {data['start_date']} >= end {data['end_date']}")
                raise serializers.ValidationError("Start date must be before end date.")
        return data

    def create(self, validated_data):
        """Override create to ensure university is set correctly."""
        university = validated_data.pop('university')
        if not isinstance(university, University) and not University.objects.filter(id=university).exists():
            raise serializers.ValidationError("Invalid university")
        validated_data['university'] = university
        return super().create(validated_data)