from django.db import models
from students.models import Admin as StudentAdmin, University

class AdminProfile(models.Model):
    """
    A profile for an admin, linked to a StudentAdmin and a University.
    The admin field serves as the primary key, ensuring a one-to-one relationship.
    """
    admin = models.OneToOneField(
        StudentAdmin,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile'
    )
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name='admin_profiles'
    )

    class Meta:
        """Ensure uniqueness of university per admin profile (optional constraint)."""
        unique_together = ['admin', 'university']

    def __str__(self):
        """Return a string representation of the admin profile."""
        return f"Profile for {self.admin.student.name if self.admin.student else 'Unknown Admin'}"