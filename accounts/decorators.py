from functools import wraps

from django.shortcuts import redirect

from .models import Distributor

# Where unauthenticated distributors land
DISTRIBUTOR_LOGIN_URL = '/distributor/login/'


def distributor_login_required(view_func):
    """Protect a view so only authenticated, active Distributor instances can
    access it.

    Unlike Django's built-in ``@login_required``, this explicitly checks that
    ``request.user`` is a ``Distributor`` instance — not just any authenticated
    object.  This means:

    - A logged-in Django admin ``User`` who navigates to a distributor URL will
      be redirected to the distributor login page (not granted access).
    - An anonymous user is redirected to the distributor login page.
    - Only an active, authenticated ``Distributor`` passes through.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if isinstance(user, Distributor) and user.is_authenticated and user.is_active:
            return view_func(request, *args, **kwargs)
        return redirect(f'{DISTRIBUTOR_LOGIN_URL}?next={request.path}')

    return wrapper
