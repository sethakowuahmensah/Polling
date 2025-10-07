from django.db import models
import pyotp

class University(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Student(models.Model):
    id = models.AutoField(primary_key=True)  # Keep id as primary key
    student_id = models.CharField(max_length=20, unique=True)  # Unique identifier
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    is_authenticated = models.BooleanField(default=False)
    can_vote = models.BooleanField(default=True)
    otp_secret = models.CharField(max_length=64, default=pyotp.random_base32)
    def generate_totp(self):
        totp = pyotp.TOTP(self.otp_secret)
        return totp.now()
    def get_totp_uri(self):
        return pyotp.totp.TOTP(self.otp_secret).provisioning_uri(
            name=self.email,
            issuer_name="GhanaSRCVoting"
        )
    def __str__(self):
        return f"{self.student_id} - {self.name}"

class Admin(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, to_field='student_id', primary_key=True)
    role = models.CharField(max_length=20, default="admin")
    name = models.CharField(max_length=100, default="")  # Ensure this is set during creation
    def __str__(self):
        return f"Admin: {self.name} ({self.student.student_id})"

class Candidate(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, to_field='student_id', primary_key=True)
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