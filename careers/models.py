from django.db import models


class CareerPageSettings(models.Model):
    """Singleton — controls the careers page hero appearance.
    Only one row should ever exist. Managed via the admin."""

    hero_image   = models.ImageField(
        upload_to='careers/hero/',
        blank=True, null=True,
        help_text='Background image for the careers hero section. '
                  'Recommended: 1920×1080 px, JPEG/PNG/WebP. Leave blank for the default gradient.'
    )
    hero_heading = models.CharField(
        max_length=200,
        default='Build your career at Aizah.',
        help_text='Main headline on the careers hero.'
    )
    hero_subtext = models.TextField(
        default='We\'re a growing FMCG manufacturer looking for people who care '
                'about quality, consistency, and doing right by our partners. '
                'Browse our open roles below.',
        help_text='Subtext paragraph under the hero headline.'
    )
    hiring_badge = models.CharField(
        max_length=60,
        default="We're hiring",
        help_text='Small badge text above the headline (e.g. "We\'re hiring").'
    )

    class Meta:
        verbose_name        = 'Career Page Settings'
        verbose_name_plural = 'Career Page Settings'

    def __str__(self):
        return 'Career Page Settings'

    @classmethod
    def get_settings(cls):
        """Returns the singleton row, creating it with defaults if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class JobPosting(models.Model):
    """An open job listing published on the careers page."""
    DEPARTMENT_CHOICES = [
        ('production', 'Production'),
        ('sales',      'Sales & Distribution'),
        ('marketing',  'Marketing'),
        ('quality',    'Quality Assurance'),
        ('logistics',  'Logistics & Supply Chain'),
        ('finance',    'Finance & Accounts'),
        ('hr',         'Human Resources'),
        ('it',         'IT & Systems'),
        ('admin',      'Administration'),
        ('other',      'Other'),
    ]

    TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract',  'Contract'),
        ('internship', 'Internship'),
    ]

    title       = models.CharField(max_length=160)
    slug        = models.SlugField(max_length=180, blank=True, null=True)
    department  = models.CharField(max_length=40, choices=DEPARTMENT_CHOICES, default='other')
    location    = models.CharField(max_length=120, default='Gazipur, Bangladesh')
    employment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='full_time')
    description = models.TextField()
    responsibilities = models.TextField(blank=True, default='')
    requirements     = models.TextField(blank=True, default='')
    deadline    = models.DateField(blank=True, null=True)

    is_open     = models.BooleanField(default=True)
    posted_at   = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_open', '-posted_at']

    def __str__(self):
        return self.title


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewing',  'Under Review'),
        ('shortlisted','Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('rejected',  'Rejected'),
        ('hired',     'Hired'),
    ]

    job          = models.ForeignKey(JobPosting, on_delete=models.CASCADE,
                                    related_name='applications')
    full_name    = models.CharField(max_length=120)
    email        = models.EmailField()
    phone        = models.CharField(max_length=40, blank=True, default='')
    cover_letter = models.TextField(blank=True, default='')
    resume       = models.FileField(upload_to='careers/resumes/', blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    applied_at   = models.DateTimeField(auto_now_add=True)

    # Google Sheets sync tracking
    synced_to_sheet = models.BooleanField(
        default=False,
        help_text='Set to True once this application has been successfully appended to Google Sheets.'
    )

    class Meta:
        ordering = ['-applied_at']

    def __str__(self):
        return '%s → %s' % (self.full_name, self.job.title)
