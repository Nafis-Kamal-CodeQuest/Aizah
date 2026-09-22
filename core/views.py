import json
import logging
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ContactInquiryForm
from .models import (
    Category, Product, ProductImage, CarouselAd, DiscountAnnouncement,
    CompanyInfo, ContactInfo,
    HomeCareCategory, HomeCareProduct, HomeCareProductImage,
)

logger = logging.getLogger(__name__)

PLACEHOLDER_IMAGE = (
    'data:image/svg+xml,'
    '%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22400%22'
    '%3E%3Crect width=%22400%22 height=%22400%22 fill=%22%23f1f5f9%22/%3E'
    '%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22'
    ' text-anchor=%22middle%22 font-family=%22sans-serif%22 font-size=%2216%22'
    ' fill=%22%2394a3b8%22%3ENo Image%3C/text%3E%3C/svg%3E'
)


def _product_image_url(product):
    url = product.image_url()
    return url if url else PLACEHOLDER_IMAGE


def _media_file_exists(media_url):
    """Verify that a media URL backed by MEDIA_ROOT actually resolves to a file
    on disk. External URLs are assumed to exist (the browser will surface a
    broken-image error if they don't)."""
    if not media_url:
        return False
    if media_url.startswith(('http://', 'https://', 'data:')):
        return True
    # Strip the MEDIA_URL prefix and resolve against MEDIA_ROOT
    prefix = settings.MEDIA_URL.rstrip('/') + '/'
    if media_url.startswith(prefix):
        rel = media_url[len(prefix):]
    else:
        rel = media_url.lstrip('/')
    target = Path(settings.MEDIA_ROOT) / rel
    return target.is_file()


def _active_scheduled(qs, active_field='active'):
    today = timezone.now().date()
    return qs.filter(**{active_field: True}).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today),
    )


def _build_carousel_slide(s):
    """Resolve a single CarouselAd into the JSON shape the template expects.

    Records an explicit `media_status` so the frontend can render a clear
    diagnostic state instead of looking like a broken hero.
    """
    media_url = s.media_url() or ''
    media_type = s.resolved_media_type()
    media_exists = _media_file_exists(media_url) if media_url else False

    if not media_url:
        media_status = 'missing_url'
    elif not media_exists:
        media_status = 'missing_file'
    else:
        media_status = 'ok'

    poster = ''

    return {
        'id': s.pk,
        'title': s.title,
        'subtitle': s.subtitle,
        'cta': s.cta_text,
        'href': s.cta_href or '#products',
        'image': media_url or PLACEHOLDER_IMAGE,
        'media_url': media_url,
        'media_type': media_type,
        'media_fit': s.media_fit,
        'poster': poster,
        'media_status': media_status,
        'tag': s.tag,
    }


def home(request):
    brand_name = 'Aizah'
    brand_full_name = 'Aizah FMCG Co. Ltd.'

    categories = list(
        Category.objects.values('name', 'slug').order_by('name')
    )

    products_qs = Product.objects.select_related('category').prefetch_related('extra_images').all()
    products = [
        {
            'id': p.sku or str(p.pk),
            'name': p.name,
            'category': p.category.name,
            'image': _product_image_url(p),
            'images': (
                [_product_image_url(p)] +
                [request.build_absolute_uri(ei.image.url) if ei.image else ''
                 for ei in p.extra_images.all()]
            ) if _product_image_url(p) else
                [request.build_absolute_uri(ei.image.url)
                 for ei in p.extra_images.all() if ei.image],
            'description': p.description,
            'specifications': p.specifications or {},
        }
        for p in products_qs
    ]

    # Home Care products — separate list, same shape as food products
    homecare_qs = HomeCareProduct.objects.select_related('category').prefetch_related('extra_images').all()
    homecare_products = [
        {
            'id': 'hc-' + (p.sku or str(p.pk)),
            'name': p.name,
            'category': p.category.name,
            'image': _product_image_url(p),
            'images': (
                [_product_image_url(p)] +
                [request.build_absolute_uri(ei.image.url) if ei.image else ''
                 for ei in p.extra_images.all()]
            ) if _product_image_url(p) else
                [request.build_absolute_uri(ei.image.url)
                 for ei in p.extra_images.all() if ei.image],
            'description': p.description,
            'specifications': p.specifications or {},
        }
        for p in homecare_qs
    ]

    homecare_categories = list(
        HomeCareCategory.objects.values('name', 'slug').order_by('name')
    )

    carousel_qs = _active_scheduled(
        CarouselAd.objects.all(), active_field='active'
    ).order_by('order')
    carousel_slides = [_build_carousel_slide(s) for s in carousel_qs]

    # Single source of truth: the carousel is driven exclusively by
    # CarouselAd rows. There is NO filesystem fallback — that fallback was
    # masking missing DB setup and making the carousel appear to behave
    # unpredictably. If no rows exist, the empty state is rendered
    # explicitly so the failure mode is obvious.

    offers_qs = _active_scheduled(
        DiscountAnnouncement.objects.all(), active_field='is_active'
    ).order_by('order', '-created_at')[:20]  # cap at 20 slides
    offers = [
        {
            'title': o.title,
            'desc': o.description,
            'badge': o.badge,
            'badgeTone': o.badge_tone,
            'image': o.image_url(),
            'image_fit': o.image_fit,
            'image_status': 'ok' if _media_file_exists(o.image_url()) else (
                'missing_file' if o.image_url() else 'missing_url'
            ),
            'meta': o.meta_text,
        }
        for o in offers_qs
    ]

    try:
        ci = CompanyInfo.objects.get()
        company = {
            'mission': ci.mission,
            'vision': ci.vision,
            'values': ci.values,
        }
    except CompanyInfo.DoesNotExist:
        company = None

    try:
        cinfo = ContactInfo.objects.get()
        contact = {
            'email': cinfo.email,
            'phone': cinfo.phone,
            'address': cinfo.address,
        }
    except ContactInfo.DoesNotExist:
        contact = None

    return render(request, 'home.html', {
        'brand_name': brand_name,
        'brand_full_name': brand_full_name,
        'carousel_slides_json': json.dumps(carousel_slides, ensure_ascii=False),
        'products_json': json.dumps(products, ensure_ascii=False),
        'homecare_products_json': json.dumps(homecare_products, ensure_ascii=False),
        'offers_json': json.dumps(offers, ensure_ascii=False),
        'categories_json': json.dumps(categories, ensure_ascii=False),
        'homecare_categories_json': json.dumps(homecare_categories, ensure_ascii=False),
        'categories': categories,
        'company': company,
        'contact': contact,
    })


@require_POST
def submit_inquiry(request):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON payload.'}, status=400)

    if 'product_interest' not in payload and 'interest' in payload:
        payload['product_interest'] = payload.pop('interest')

    form = ContactInquiryForm(payload)
    if form.is_valid():
        form.save()
        return JsonResponse({
            'ok': True,
            'message': ('Thank you \u2014 your inquiry has been received. '
                       'Our trade desk will respond within one business day.'),
        })
    errors = {f: e[0] for f, e in form.errors.items()}
    return JsonResponse({'ok': False, 'errors': errors}, status=422)
