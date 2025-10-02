from rest_framework import serializers
from .models import SuperAdmin
import pyotp

class SuperAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdmin
        fields = ['id', 'name', 'email', 'phone_number', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password')
        admin = SuperAdmin(**validated_data)
        admin.set_password(password)
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
