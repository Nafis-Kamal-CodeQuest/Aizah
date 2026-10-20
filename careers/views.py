import json
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import JobPosting, JobApplication, CareerPageSettings

logger = logging.getLogger(__name__)


def careers(request):
    """Careers landing page — lists open job postings and a multi-step
    application form. Openings are injected as JSON for the client-side
    card grid + filtering, mirroring the pattern used by home.html."""

    today = timezone.now().date()

    jobs_qs = (
        JobPosting.objects
        .filter(is_open=True)
        .filter(Q(deadline__isnull=True) | Q(deadline__gte=today))
        .order_by('-posted_at')
    )

    jobs = [
        {
            'id':             j.pk,
            'title':          j.title,
            'department':     j.get_department_display(),
            'department_key': j.department,
            'location':       j.location,
            'type':           j.get_employment_type_display(),
            'type_key':       j.employment_type,
            'description':    j.description,
            'responsibilities': j.responsibilities,
            'requirements':     j.requirements,
            'deadline':       j.deadline.isoformat() if j.deadline else '',
            'posted_at':      j.posted_at.date().isoformat() if j.posted_at else '',
        }
        for j in jobs_qs
    ]

    # Pass contact info (mirrors home.html pattern — try/except, fallback None)
    from core.models import CompanyInfo, ContactInfo
    try:
        ci      = CompanyInfo.objects.get()
        company = {'mission': ci.mission, 'vision': ci.vision, 'values': ci.values}
    except CompanyInfo.DoesNotExist:
        company = None

    try:
        cinfo   = ContactInfo.objects.get()
        contact = {'email': cinfo.email, 'phone': cinfo.phone, 'address': cinfo.address}
    except ContactInfo.DoesNotExist:
        contact = None

    return render(request, 'careers.html', {
        'brand_name':      'Aizah',
        'brand_full_name': 'Aizah FMCG Co. Ltd.',
        'jobs_json':       json.dumps(jobs, ensure_ascii=False),
        'company':         company,
        'contact':         contact,
        'hero':            CareerPageSettings.get_settings(),
    })


@require_POST
def apply(request):
    """Async form submit endpoint. Accepts multipart/form-data so the
    resume file uploads cleanly. Returns JSON for the frontend handler."""
    job_id = request.POST.get('job_id')
    if not job_id:
        return JsonResponse({'ok': False, 'error': 'Missing job_id.'}, status=400)

    job = get_object_or_404(JobPosting, pk=job_id, is_open=True)

    application = JobApplication(job=job)
    application.full_name    = (request.POST.get('full_name') or '').strip()
    application.email        = (request.POST.get('email') or '').strip()
    application.phone        = (request.POST.get('phone') or '').strip()
    application.cover_letter = (request.POST.get('cover_letter') or '').strip()

    # Validate manually so we can return clean field errors as JSON
    try:
        application.full_clean(exclude=['resume'])
    except ValidationError as e:
        return JsonResponse({'ok': False, 'errors': e.message_dict}, status=422)

    # Optional resume upload — restrict to 5 MB and common document types
    resume = request.FILES.get('resume')
    if resume:
        max_size = 5 * 1024 * 1024
        if resume.size > max_size:
            return JsonResponse({
                'ok': False,
                'errors': {'resume': 'Resume must be under 5 MB.'}
            }, status=422)
        allowed = ('.pdf', '.doc', '.docx', '.odt', '.rtf', '.txt')
        if not resume.name.lower().endswith(allowed):
            return JsonResponse({
                'ok': False,
                'errors': {
                    'resume': 'Resume must be a PDF, DOC, DOCX, ODT, RTF or TXT file.'
                }
            }, status=422)
        application.resume = resume

    application.save()

    return JsonResponse({
        'ok': True,
        'message': ('Thank you for applying. We have received your application '
                    'and will reach out to shortlisted candidates.')
    })
