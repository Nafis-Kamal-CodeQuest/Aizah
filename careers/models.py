from django.db import models


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

    class Meta:
        ordering = ['-applied_at']

    def __str__(self):
        return '%s → %s' % (self.full_name, self.job.title)
