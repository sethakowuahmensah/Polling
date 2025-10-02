from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import pyotp

class SuperAdminManager(BaseUserManager):
    def create_superuser(self, email, name, phone_number, password):
        email = self.normalize_email(email)
        superadmin = self.model(
            email=email,
            name=name,
            phone_number=phone_number,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        superadmin.set_password(password)
        superadmin.save(using=self._db)
        return superadmin

    def create_user(self, email, name, phone_number, password=None):
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, phone_number=phone_number)
        user.set_password(password)
        user.save(using=self._db)
        return user

class SuperAdmin(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='superadmin_set',
        blank=True,
        help_text='Groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='superadmin_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    # 2FA Fields
    two_fa_enabled = models.BooleanField(default=False)
    two_fa_secret = models.CharField(max_length=64, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'phone_number']

    objects = SuperAdminManager()

    def __str__(self):
        return self.email

    @classmethod
    def create_default_superadmin(cls):
        if not cls.objects.filter(email="sethakowuahmensah@gmail.com").exists():
            cls.objects.create_superuser(
                email="sethakowuahmensah@gmail.com",
                name="Sam Flex",
                phone_number="+233277935236",
                password="password100"
            )

    # Google Authenticator TOTP
    def generate_2fa_secret(self):
        if not self.two_fa_secret:
            self.two_fa_secret = pyotp.random_base32()
            self.save()
        return self.two_fa_secret

    def get_totp_uri(self):
        self.generate_2fa_secret()
        return pyotp.totp.TOTP(self.two_fa_secret).provisioning_uri(
            name=self.email, issuer_name="YourAppName"
        )

    def verify_totp(self, token):
        if not self.two_fa_secret:
            return False
        totp = pyotp.TOTP(self.two_fa_secret)
        return totp.verify(token)
