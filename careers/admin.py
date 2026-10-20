from django.contrib import admin

from .models import JobPosting, JobApplication


class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0
    readonly_fields = ('full_name', 'email', 'phone', 'cover_letter',
                       'resume', 'applied_at')
    can_delete = True
    ordering = ['-applied_at']


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'location', 'employment_type',
                    'is_open', 'posted_at', 'deadline')
    list_filter = ('is_open', 'department', 'employment_type')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-is_open', '-posted_at']
    inlines = [JobApplicationInline]
    fieldsets = (
        ('Role', {
            'fields': ('title', 'slug', 'department', 'location', 'employment_type')
        }),
        ('Content', {
            'fields': ('description', 'responsibilities', 'requirements')
        }),
        ('Lifecycle', {
            'fields': ('deadline', 'is_open')
        }),
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job', 'email', 'status', 'applied_at')
    list_filter = ('status', 'job')
    search_fields = ('full_name', 'email', 'phone', 'cover_letter')
    readonly_fields = ('applied_at',)
    ordering = ['-applied_at']
    list_editable = ('status',)
