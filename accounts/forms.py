import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Distributor


# ---------------------------------------------------------------------------
# Distributor portal login form (used by distributor-facing views)
# ---------------------------------------------------------------------------

class DistributorLoginForm(forms.Form):
    """Login form for the distributor portal.

    Validates presence and basic format only — credential verification is
    done in the view via ``authenticate()``.
    """

    distributor_code = forms.CharField(
        label='Distributor Code',
        max_length=20,
        strip=True,
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'placeholder': 'e.g. DIST001',
            'class': (
                'w-full px-4 py-3 rounded-lg border border-slate-300 '
                'bg-white text-slate-900 placeholder-slate-400 '
                'focus:outline-none focus:ring-2 focus:ring-brand-500 '
                'focus:border-brand-500 transition text-sm'
            ),
        }),
    )

    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'placeholder': '••••••••',
            'class': (
                'w-full px-4 py-3 rounded-lg border border-slate-300 '
                'bg-white text-slate-900 placeholder-slate-400 '
                'focus:outline-none focus:ring-2 focus:ring-brand-500 '
                'focus:border-brand-500 transition text-sm'
            ),
        }),
    )

    def clean_distributor_code(self):
        return self.cleaned_data['distributor_code'].strip().upper()


# ---------------------------------------------------------------------------
# Admin forms — used exclusively inside Django admin (/admin)
# ---------------------------------------------------------------------------

_CODE_RE = re.compile(r'^[A-Z0-9_-]{1,20}$')


def _validate_distributor_code(value):
    if not _CODE_RE.match(value.upper()):
        raise ValidationError(
            'Distributor code must be 1–20 characters, letters, digits, '
            'hyphens, or underscores only.'
        )


class DistributorAdminAddForm(forms.ModelForm):
    """Used when an admin creates a brand-new distributor.

    Requires an initial password (entered twice for confirmation).
    The plaintext is never stored — ``set_password()`` is called in
    ``DistributorAdmin.save_model()``.
    """

    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='At least 8 characters.',
    )
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = Distributor
        fields = ['distributor_code', 'name', 'business_name', 'phone', 'is_active']

    def clean_distributor_code(self):
        code = self.cleaned_data['distributor_code'].strip().upper()
        _validate_distributor_code(code)
        if Distributor.objects.filter(distributor_code=code).exists():
            raise ValidationError('A distributor with this code already exists.')
        return code

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise ValidationError('Phone number is required.')
        if len(phone) > 30:
            raise ValidationError('Phone must be 30 characters or fewer.')
        return phone

    def clean_password1(self):
        pw = self.cleaned_data.get('password1', '')
        if len(pw) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return pw

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('password1', '')
        pw2 = cleaned.get('password2', '')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned


class DistributorAdminChangeForm(forms.ModelForm):
    """Used when an admin edits an existing distributor.

    Password is NOT shown here — use the dedicated "Reset password" action
    instead.  This keeps the change form clean and avoids accidental password
    overwrites.
    """

    class Meta:
        model = Distributor
        fields = ['distributor_code', 'name', 'business_name', 'phone', 'is_active']

    def clean_distributor_code(self):
        code = self.cleaned_data['distributor_code'].strip().upper()
        _validate_distributor_code(code)
        qs = Distributor.objects.filter(distributor_code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('A distributor with this code already exists.')
        return code

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise ValidationError('Phone number is required.')
        if len(phone) > 30:
            raise ValidationError('Phone must be 30 characters or fewer.')
        return phone


class DistributorPasswordResetForm(forms.Form):
    """Standalone form rendered by the admin "Reset password" action view."""

    new_password1 = forms.CharField(
        label='New password',
        strip=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='At least 8 characters.',
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def clean_new_password1(self):
        pw = self.cleaned_data.get('new_password1', '')
        if len(pw) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return pw

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('new_password1', '')
        pw2 = cleaned.get('new_password2', '')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('new_password2', 'Passwords do not match.')
        return cleaned
