from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.contrib.auth.hashers import make_password
import pyotp

class StudentManager(BaseUserManager):
    def create_user(self, student_id, email, name, password=None, **extra_fields):
        if not student_id:
            raise ValueError("The student_id must be set")
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        user = self.model(student_id=student_id, email=email, name=name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.password = None  # allows null passwords initially
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if not password:
            raise ValueError("Superusers must have a password.")
        return self.create_user(student_id, email, name, password, **extra_fields)

class University(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Student(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE, null=True, blank=True)
    # login / account flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # application specific
    can_vote = models.BooleanField(default=True)
    otp_secret = models.CharField(max_length=64, default=pyotp.random_base32)
    password = models.CharField(max_length=128, null=True, blank=True)  # now nullable
    is_verified = models.BooleanField(default=False)  # New field to track verification
    otp_temp = models.CharField(max_length=6, null=True, blank=True)    # Field for temporary OTP
    otp_expiry_temp = models.DateTimeField(null=True, blank=True)       # Field for OTP expiry time
    objects = StudentManager()
    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['email', 'name']

    def save(self, *args, **kwargs):
        # Automatically hash password if it’s not already hashed
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def generate_totp(self):
        return pyotp.TOTP(self.otp_secret).now()

    def get_totp_uri(self):
        return pyotp.TOTP(self.otp_secret).provisioning_uri(
            name=self.email or self.student_id,
            issuer_name="GhanaSRCVoting"
        )

    def __str__(self):
        return f"{self.student_id} - {self.name}"

class Admin(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        to_field='student_id',
        primary_key=True
    )
    role = models.CharField(max_length=20, default="admin")
    name = models.CharField(max_length=100, default="")
    def __str__(self):
        return f"Admin: {self.name} ({self.student.student_id})"

class Candidate(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        to_field='student_id',
        primary_key=True
    )
    nomination_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"Candidate: {self.student.name} ({self.student.student_id})"

class Election(models.Model):
    name = models.CharField(max_length=100)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.name} - {self.university.name}"