from django.db import models
from students.models import Student, University, Admin as StudentAdmin, Candidate, Election

# Optionally extend Admin model or use existing one
class AdminProfile(models.Model):
    admin = models.OneToOneField(StudentAdmin, on_delete=models.CASCADE, primary_key=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)  # Link to admin's university
    def __str__(self):
        return f"Admin: {self.admin.student.name} ({self.university.name})"