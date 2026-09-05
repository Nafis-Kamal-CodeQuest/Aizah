from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class DistributorManager(BaseUserManager):
    """Custom manager for the Distributor model.

    Deliberately does NOT provide create_superuser — distributors must never
    become admin users via any code path.
    """

    def create_distributor(self, distributor_code, name, phone, password, **extra_fields):
        if not distributor_code:
            raise ValueError('distributor_code is required')
        if not name:
            raise ValueError('name is required')
        if not phone:
            raise ValueError('phone is required')
        if not password:
            raise ValueError('password is required')

        distributor = self.model(
            distributor_code=distributor_code.strip().upper(),
            name=name.strip(),
            phone=phone.strip(),
            **extra_fields,
        )
        distributor.set_password(password)
        distributor.save(using=self._db)
        return distributor

    def get_by_natural_key(self, distributor_code):
        """Required by AbstractBaseUser authentication machinery."""
        return self.get(distributor_code=distributor_code)


class Distributor(AbstractBaseUser):
    """A completely separate user type from auth.User.

    - No is_staff / is_superuser fields — structurally impossible to pass an
      admin permission check.
    - Uses distributor_code (short alphanumeric, upper-cased) as the login
      credential identifier.
    - Password is hashed via Django's standard password hashers (PBKDF2 by
      default) through AbstractBaseUser.set_password().
    - Django's session middleware stores the authenticated object in the
      session normally; the DistributorBackend ensures only Distributor
      instances come back from that session key.
    """

    distributor_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique alphanumeric code assigned by admin (e.g. DIST001). '
                  'Saved as uppercase. Used as login username.',
    )
    name = models.CharField(max_length=200)
    business_name = models.CharField(max_length=200, blank=True, default='')
    phone = models.CharField(max_length=30)

    is_active = models.BooleanField(
        default=True,
        help_text='Deactivate to block login without deleting the account.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tell AbstractBaseUser which field is the "username"
    USERNAME_FIELD = 'distributor_code'

    # Fields that manage.py createsuperuser would prompt for (irrelevant here,
    # but required by the interface — we leave it minimal).
    REQUIRED_FIELDS = ['name', 'phone']

    objects = DistributorManager()

    class Meta:
        verbose_name = 'Distributor'
        verbose_name_plural = 'Distributors'
        ordering = ['distributor_code']

    def __str__(self):
        return f'{self.distributor_code} — {self.name}'

    def save(self, *args, **kwargs):
        # Always store the code in uppercase so lookups are case-insensitive
        # by convention.
        self.distributor_code = self.distributor_code.strip().upper()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Explicitly block any path that could grant admin access.
    # The Django admin site checks has_module_perms / has_perm before
    # rendering any admin view; returning False unconditionally ensures
    # a Distributor object can never see or use /admin even if it somehow
    # ends up in request.user there.
    # ------------------------------------------------------------------

    def has_perm(self, perm, obj=None):
        return False

    def has_module_perms(self, app_label):
        return False

    @property
    def is_staff(self):
        """Always False — distributors are never staff."""
        return False
