import secrets
import string

from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import (
    DistributorAdminAddForm,
    DistributorAdminChangeForm,
    DistributorPasswordResetForm,
)
from .models import Distributor


def _generate_password(length=12):
    """Generate a secure random password to display once on creation."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = [
        'distributor_code', 'name', 'business_name', 'phone',
        'active_badge', 'created_at', 'row_actions',
    ]
    list_filter  = ['is_active', 'created_at']
    search_fields = ['distributor_code', 'name', 'business_name', 'phone']
    ordering = ['distributor_code']
    readonly_fields = ['created_at', 'updated_at']

    # ------------------------------------------------------------------
    # Form selection: add vs change
    # ------------------------------------------------------------------
    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = DistributorAdminAddForm
        else:
            kwargs['form'] = DistributorAdminChangeForm
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        if obj is None:
            # Add form — include password fields
            return [
                'distributor_code', 'name', 'business_name',
                'phone', 'is_active', 'password1', 'password2',
            ]
        # Change form — no password fields; use Reset Password action instead
        return [
            'distributor_code', 'name', 'business_name',
            'phone', 'is_active', 'created_at', 'updated_at',
        ]

    # ------------------------------------------------------------------
    # Save: hash password on create
    # ------------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        if not change:
            # New distributor — set hashed password from the form
            obj.set_password(form.cleaned_data['password1'])
        obj.save()

    # ------------------------------------------------------------------
    # Delete: soft-delete (deactivate) when distributor has orders,
    # hard-delete otherwise.  Confirmation happens via the standard
    # Django delete confirmation page; we override the actual deletion.
    # ------------------------------------------------------------------
    def delete_model(self, request, obj):
        # Import here to avoid a circular import before the Order model
        # exists; gracefully falls back to hard-delete if orders app is
        # not yet present.
        try:
            from core.models import Order  # noqa: F401 — existence check
            has_orders = obj.orders.exists()
        except (ImportError, AttributeError):
            has_orders = False

        if has_orders:
            obj.is_active = False
            obj.save(update_fields=['is_active'])
            self.message_user(
                request,
                f'Distributor "{obj}" has order history and was deactivated '
                f'instead of deleted.',
                level=messages.WARNING,
            )
        else:
            obj.delete()

    # ------------------------------------------------------------------
    # Bulk actions
    # ------------------------------------------------------------------
    actions = ['deactivate_distributors', 'reactivate_distributors']

    @admin.action(description='Deactivate selected distributors')
    def deactivate_distributors(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'{updated} distributor(s) deactivated.',
            level=messages.SUCCESS,
        )

    @admin.action(description='Reactivate selected distributors')
    def reactivate_distributors(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'{updated} distributor(s) reactivated.',
            level=messages.SUCCESS,
        )

    # ------------------------------------------------------------------
    # Custom URL: /admin/accounts/distributor/<pk>/reset-password/
    # ------------------------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/reset-password/',
                self.admin_site.admin_view(self.reset_password_view),
                name='accounts_distributor_reset_password',
            ),
        ]
        return custom + urls

    def reset_password_view(self, request, pk):
        """Intermediate view for the Reset Password action.

        GET  — renders a two-field password form.
        POST — validates, hashes, saves, redirects back to change page.
        """
        distributor = get_object_or_404(Distributor, pk=pk)

        if request.method == 'POST':
            form = DistributorPasswordResetForm(request.POST)
            if form.is_valid():
                distributor.set_password(form.cleaned_data['new_password1'])
                distributor.save(update_fields=['password', 'updated_at'])
                self.message_user(
                    request,
                    f'Password for "{distributor}" has been reset successfully.',
                    level=messages.SUCCESS,
                )
                return redirect(
                    reverse(
                        'admin:accounts_distributor_change',
                        args=[distributor.pk],
                    )
                )
        else:
            form = DistributorPasswordResetForm()

        context = {
            **self.admin_site.each_context(request),
            'title': f'Reset password — {distributor}',
            'distributor': distributor,
            'form': form,
            'opts': self.model._meta,
        }
        return render(request, 'admin/accounts/distributor/reset_password.html', context)

    # ------------------------------------------------------------------
    # List display helpers
    # ------------------------------------------------------------------
    @admin.display(description='Active', ordering='is_active')
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="'
                'display:inline-block;padding:2px 10px;border-radius:9999px;'
                'background:#d1fae5;color:#065f46;font-size:11px;font-weight:600;">'
                '&#10003; Active</span>'
            )
        return format_html(
            '<span style="'
            'display:inline-block;padding:2px 10px;border-radius:9999px;'
            'background:#fee2e2;color:#991b1b;font-size:11px;font-weight:600;">'
            '&#10005; Inactive</span>'
        )

    @admin.display(description='Actions')
    def row_actions(self, obj):
        change_url = reverse('admin:accounts_distributor_change', args=[obj.pk])
        reset_url  = reverse('admin:accounts_distributor_reset_password', args=[obj.pk])
        return format_html(
            '<a href="{}" style="margin-right:8px;">Edit</a>'
            '<a href="{}">Reset password</a>',
            change_url,
            reset_url,
        )
