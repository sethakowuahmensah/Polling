from django.db import models
from students.models import Admin, University


class AdminProfile(models.Model):
    admin = models.OneToOneField(
        Admin,
        on_delete=models.CASCADE,
        primary_key=True
    )
    university = models.ForeignKey(University, on_delete=models.CASCADE)

    def __str__(self):
        return f"Profile for {self.admin.name}"
