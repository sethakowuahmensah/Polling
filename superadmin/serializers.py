from rest_framework import serializers
from .models import SuperAdmin, Admin, Student
import pyotp


# ================= SuperAdmin =================
class SuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = ['id', 'name', 'email', 'phone_number', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        admin = SuperAdmin(**validated_data)
        admin.set_password(password)
        admin.save()  # persist
        return admin


class SuperAdmin2FASerializer(serializers.Serializer):
    """Serializer for handling 2FA code verification"""
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, required=False)

    def generate_google_auth_secret(self, admin):
        """Generate secret for Google Authenticator"""
        if not admin.two_fa_secret:
            secret = pyotp.random_base32()
            admin.two_fa_secret = secret
            admin.save()
        return admin.two_fa_secret

    def verify_google_auth_code(self, admin, code):
        """Verify code from Google Authenticator app"""
        if not admin.two_fa_secret:
            return False
        totp = pyotp.TOTP(admin.two_fa_secret)
        return totp.verify(code)


# ================= Bulk Import Serializer =================
class BulkUserSerializer(serializers.Serializer):
    """
    Serializer to import students or admins in bulk.
    role can be 'student' or 'admin'.
    """
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=["student", "admin"], default="student")

    def create(self, validated_data):
        role = validated_data.pop('role', 'student')
        password = validated_data.pop('password')

        if role == "admin":
            user = Admin(**validated_data)
        else:
            user = Student(**validated_data)

        user.set_password = lambda x: None  # placeholder for Student/Admin
        # store password as is or hash externally if needed

        user.save()
        return user


# ================= Role Update Serializer =================
class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["student", "admin"])

    def update_role(self, user_instance, new_role):
        """Update role of student/admin (superadmin only)"""
        if isinstance(user_instance, Student) and new_role == "admin":
            # convert Student -> Admin
            admin = Admin(
                name=user_instance.name,
                email=user_instance.email,
                phone_number=user_instance.phone_number,
                role="admin",
                date_joined=user_instance.date_joined
            )
            admin.save()
            user_instance.delete()
            return admin

        elif isinstance(user_instance, Admin) and new_role == "student":
            # convert Admin -> Student
            student = Student(
                name=user_instance.name,
                email=user_instance.email,
                phone_number=user_instance.phone_number,
                role="student",
                date_joined=user_instance.date_joined
            )
            student.save()
            user_instance.delete()
            return student

        return user_instance  # no change
