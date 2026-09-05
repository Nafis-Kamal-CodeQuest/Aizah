from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import ContactInquiry


class ContactInquiryForm(forms.ModelForm):
    name = forms.CharField(required=False)
    company = forms.CharField(required=False)
    email = forms.CharField(required=False)
    phone = forms.CharField(required=False)
    product_interest = forms.CharField(required=False)
    message = forms.CharField(required=False)

    class Meta:
        model = ContactInquiry
        fields = ['name', 'company', 'email', 'phone', 'product_interest', 'message']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('Name is required.')
        if len(name) > 200:
            raise ValidationError('Name must be 200 characters or fewer.')
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise ValidationError('Email address is required.')
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError('Enter a valid email address.')
        if len(email) > 254:
            raise ValidationError('Email address is too long.')
        return email.lower()

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and len(phone) > 30:
            raise ValidationError('Phone number must be 30 characters or fewer.')
        return phone

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        # Soft cap — warn rather than hard-reject so genuine long messages
        # still go through, but prevent trivially large payloads.
        if len(message) > 5000:
            raise ValidationError('Message must be 5,000 characters or fewer.')
        return message

    def clean_product_interest(self):
        interest = self.cleaned_data.get('product_interest', '').strip()
        if not interest:
            return ''
        valid_choices = {choice for choice, _label in ContactInquiry.PRODUCT_INTEREST_CHOICES}
        if interest not in valid_choices:
            raise ValidationError('Select a valid product interest.')
        return interest
