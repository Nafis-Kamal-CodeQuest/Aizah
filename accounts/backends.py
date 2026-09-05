from django.contrib.auth.backends import BaseBackend

from .models import Distributor


class DistributorBackend(BaseBackend):
    """Authentication backend exclusively for Distributor accounts.

    - Only ever returns a ``Distributor`` instance, never an ``auth.User``.
    - Only activates when ``distributor_code`` is supplied as a keyword
      argument; ``django.contrib.auth.backends.ModelBackend`` (the default)
      will never call this path and this backend will never handle its calls.
    - Inactive distributors are silently rejected (``None`` returned).
    - The Django admin uses ``ModelBackend`` and checks ``is_staff``; because
      ``Distributor.is_staff`` is always ``False`` and this backend only
      returns ``Distributor`` objects, an authenticated distributor can never
      gain access to ``/admin``.
    """

    def authenticate(self, request, distributor_code=None, password=None, **kwargs):
        if distributor_code is None or password is None:
            # Not our credentials — let the next backend try.
            return None

        try:
            distributor = Distributor.objects.get(
                distributor_code=distributor_code.strip().upper()
            )
        except Distributor.DoesNotExist:
            # Run a dummy password check to resist timing attacks.
            Distributor().check_password(password)
            return None

        if not distributor.check_password(password):
            return None

        if not distributor.is_active:
            return None

        return distributor

    def get_user(self, user_id):
        """Called by Django's session machinery to rehydrate the user object
        from the session on subsequent requests.

        We only handle ``Distributor`` PKs here; if the PK belongs to an
        ``auth.User`` this method returns ``None`` and the default backend
        handles it instead (and vice-versa).
        """
        try:
            distributor = Distributor.objects.get(pk=user_id)
        except Distributor.DoesNotExist:
            return None

        return distributor if distributor.is_active else None
