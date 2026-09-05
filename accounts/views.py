from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Category, Order, OrderItem, Product
from .decorators import distributor_login_required
from .forms import DistributorLoginForm
from .models import Distributor

_LOGIN_URL      = 'accounts:distributor_login'
_DEFAULT_REDIRECT = 'accounts:distributor_dashboard'

PLACEHOLDER_IMAGE = (
    'data:image/svg+xml,'
    '%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22400%22'
    '%3E%3Crect width=%22400%22 height=%22400%22 fill=%22%23f1f5f9%22/%3E'
    '%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22'
    ' text-anchor=%22middle%22 font-family=%22sans-serif%22 font-size=%2216%22'
    ' fill=%22%2394a3b8%22%3ENo Image%3C/text%3E%3C/svg%3E'
)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def distributor_login(request):
    """GET: render login form. POST: authenticate and start session."""
    if isinstance(request.user, Distributor) and request.user.is_authenticated:
        return redirect(_DEFAULT_REDIRECT)

    next_url = request.GET.get('next') or request.POST.get('next', '')

    if request.method == 'POST':
        form = DistributorLoginForm(request.POST)
        if form.is_valid():
            distributor = authenticate(
                request,
                distributor_code=form.cleaned_data['distributor_code'],
                password=form.cleaned_data['password'],
            )
            if distributor is not None:
                login(request, distributor,
                      backend='accounts.backends.DistributorBackend')
                messages.success(request, f'Welcome back, {distributor.name}.')
                safe = _safe_next(next_url)
                return redirect(safe or _DEFAULT_REDIRECT)
            else:
                messages.error(
                    request,
                    'Invalid distributor code or password. '
                    'Please check your credentials and try again.',
                )
    else:
        form = DistributorLoginForm()

    return render(request, 'distributor/login.html', {
        'form': form,
        'next': next_url,
    })


def distributor_logout(request):
    """POST → log out and redirect to login.
    GET  → show a confirmation page (protects against CSRF-logout from
           third-party pages; the navbar Sign-out link submits a tiny form).
    """
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect(_LOGIN_URL)
    # GET — render a one-click confirmation so the link in the nav still works
    # without being a CSRF vector.
    return render(request, 'distributor/logout_confirm.html')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@distributor_login_required
def distributor_dashboard(request):
    dist = request.user
    counts = {
        'pending':   dist.orders.filter(status=Order.STATUS_PENDING).count(),
        'confirmed': dist.orders.filter(status=Order.STATUS_CONFIRMED).count(),
        'fulfilled': dist.orders.filter(status=Order.STATUS_FULFILLED).count(),
        'total':     dist.orders.count(),
    }
    recent_orders = (
        dist.orders
        .prefetch_related('items__product')
        .order_by('-created_at')[:5]
    )
    return render(request, 'distributor/dashboard.html', {
        'distributor':    dist,
        'counts':         counts,
        'recent_orders':  recent_orders,
    })


# ---------------------------------------------------------------------------
# Catalog + order placement
# ---------------------------------------------------------------------------

@distributor_login_required
def distributor_catalog(request):
    """Browse all products and submit a new order with quantities.

    POST body: one ``qty_<product_pk>`` field per product the distributor
    wants to include.  Products with qty=0 or blank are skipped.
    A note field (optional) is attached to the Order.
    """
    categories = Category.objects.prefetch_related('products').order_by('name')

    # Build flat product list with image URLs for the template
    products_qs = (
        Product.objects
        .select_related('category')
        .order_by('category__name', 'name')
    )
    products = [
        {
            'obj':   p,
            'image': p.image_url() or PLACEHOLDER_IMAGE,
        }
        for p in products_qs
    ]

    if request.method == 'POST':
        note = request.POST.get('note', '').strip()[:2000]  # hard cap — model is TextField
        items = []

        for p in products_qs:
            raw = request.POST.get(f'qty_{p.pk}', '').strip()
            if not raw:
                continue
            try:
                qty = int(raw)
            except ValueError:
                messages.error(
                    request,
                    f'Invalid quantity for "{p.name}" — please enter a whole number.',
                )
                return render(request, 'distributor/catalog.html', {
                    'categories': categories,
                    'products':   products,
                })
            if qty < 0:
                messages.error(
                    request,
                    f'Quantity for "{p.name}" cannot be negative.',
                )
                return render(request, 'distributor/catalog.html', {
                    'categories': categories,
                    'products':   products,
                })
            if qty > 0:
                items.append((p, qty))

        if not items:
            messages.error(
                request,
                'Please enter a quantity of at least 1 for one or more products.',
            )
            return render(request, 'distributor/catalog.html', {
                'categories': categories,
                'products':   products,
            })

        with transaction.atomic():
            order = Order.objects.create(
                distributor=request.user,
                note=note,
            )
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product=p, quantity=qty)
                for p, qty in items
            ])

        messages.success(
            request,
            f'Order #{order.pk} submitted successfully. '
            f'We will confirm it shortly.',
        )
        return redirect('accounts:order_detail', pk=order.pk)

    return render(request, 'distributor/catalog.html', {
        'categories': categories,
        'products':   products,
    })


# ---------------------------------------------------------------------------
# Order history
# ---------------------------------------------------------------------------

@distributor_login_required
def distributor_order_history(request):
    """List all orders belonging to the current distributor only."""
    status_filter = request.GET.get('status', '')
    orders_qs = (
        request.user.orders
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    if status_filter and status_filter in dict(Order.STATUS_CHOICES):
        orders_qs = orders_qs.filter(status=status_filter)

    return render(request, 'distributor/order_history.html', {
        'orders':        orders_qs,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    })


# ---------------------------------------------------------------------------
# Order detail
# ---------------------------------------------------------------------------

@distributor_login_required
def distributor_order_detail(request, pk):
    """Single order detail — enforces ownership so a distributor can never
    view another distributor's order by guessing the PK."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        pk=pk,
        distributor=request.user,   # ownership check
    )
    return render(request, 'distributor/order_detail.html', {
        'order': order,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_next(next_url):
    if not next_url:
        return None
    if next_url.startswith(('http://', 'https://', '//', ' ')):
        return None
    if next_url.lstrip('/').startswith('admin'):
        return None
    return next_url
