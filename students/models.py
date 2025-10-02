from django.db import models
import pyotp

class University(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    is_authenticated = models.BooleanField(default=False)
    
    # Google Authenticator TOTP secret (increased length to avoid DB errors)
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


class Candidate(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=50)
    university = models.ForeignKey(University, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.position})"


class Vote(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'candidate')

    def __str__(self):
        return f"{self.student} voted for {self.candidate}"
