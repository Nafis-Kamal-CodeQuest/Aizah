import json

from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Category, Product, ProductImage, CarouselAd, DiscountAnnouncement,
    CompanyInfo, ContactInfo, ContactInquiry,
    HomeCareCategory, HomeCareProduct, HomeCareProductImage,
    Order, OrderItem,
)


class ProductAdminForm(forms.ModelForm):
    specifications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 8}),
        help_text='Enter JSON, label/value lines, or plain text. Plain text will be saved as a single value.',
    )

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = self.initial.get('specifications')
        if value is None and self.instance and self.instance.pk:
            value = self.instance.specifications
        if isinstance(value, (dict, list)):
            self.fields['specifications'].initial = json.dumps(value, indent=2, ensure_ascii=False)
        elif value not in (None, ''):
            self.fields['specifications'].initial = value

    def clean_specifications(self):
        raw_value = self.cleaned_data.get('specifications', '')
        if raw_value in (None, ''):
            return {}

        if isinstance(raw_value, (dict, list)):
            return raw_value

        text = str(raw_value).strip()
        if not text:
            return {}

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        else:
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {'items': parsed}
            return {'value': parsed}

        parsed_lines = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            separator = ':' if ':' in line else '=' if '=' in line else None
            if not separator:
                parsed_lines = {}
                break
            key, value = line.split(separator, 1)
            key = key.strip()
            value = value.strip()
            if not key or not value:
                parsed_lines = {}
                break
            parsed_lines[key] = value

        if parsed_lines:
            return parsed_lines

        return {'value': text}

    def clean_sku(self):
        sku = self.cleaned_data.get('sku', '')
        if sku is None:
            return None

        sku = str(sku).strip()
        return sku or None


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    inlines = [ProductImageInline]
    list_display = ['name', 'sku', 'category', 'image_preview', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    list_select_related = ['category']
    autocomplete_fields = ['category']
    fields = ['category', 'name', 'sku', 'description', 'specifications', 'image', 'external_image_url', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def image_preview(self, obj):
        url = obj.image_url()
        if not url:
            return 'No Image'
        return format_html(
            '<img src="{}" style="height: 50px; border-radius: 4px;" />',
            url,
        )
    image_preview.short_description = 'Preview'


@admin.register(CarouselAd)
class CarouselAdAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'media_type', 'media_fit', 'media_preview', 'order', 'active', 'start_date', 'end_date']
    list_editable = ['order', 'active']
    list_filter = ['media_type', 'media_fit', 'active']
    ordering = ['order']
    fields = ['title', 'subtitle', 'tag', 'cta_text', 'cta_href', 'media_type', 'media_file', 'external_image_url', 'media_fit', 'order', 'active', 'start_date', 'end_date', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def media_preview(self, obj):
        url = obj.media_url()
        if not url:
            return 'No Media'
        if obj.resolved_media_type() == 'video':
            return format_html(
                '<video src="{}" style="height: 60px;" controls></video>',
                url,
            )
        return format_html(
            '<img src="{}" style="height: 60px; border-radius: 4px; object-fit: contain;" />',
            url,
        )
    media_preview.short_description = 'Preview'


@admin.register(DiscountAnnouncement)
class DiscountAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'image_preview', 'image_fit', 'badge', 'order', 'is_active', 'start_date', 'end_date', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active', 'image_fit']
    ordering = ['order', '-created_at']
    fields = ['title', 'description', 'badge', 'badge_tone', 'image', 'external_image_url', 'image_fit', 'meta_text', 'order', 'is_active', 'start_date', 'end_date', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def image_preview(self, obj):
        url = obj.image_url()
        if not url:
            return 'No Image'
        return format_html(
            '<img src="{}" style="height: 50px; width: 80px; object-fit: contain; border-radius: 4px;" />',
            url,
        )
    image_preview.short_description = 'Preview'


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'updated_at']

    def has_add_permission(self, request):
        if CompanyInfo.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'email', 'phone', 'updated_at']

    def has_add_permission(self, request):
        if ContactInfo.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'product_interest', 'created_at']
    list_filter = ['product_interest', 'created_at']
    search_fields = ['name', 'email', 'company']
    readonly_fields = ['created_at']


# ---------------------------------------------------------------------------
# Home Care
# ---------------------------------------------------------------------------

@admin.register(HomeCareCategory)
class HomeCareCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


class HomeCareProductAdminForm(forms.ModelForm):
    specifications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 8}),
        help_text='Enter JSON, label/value lines, or plain text.',
    )

    class Meta:
        model = HomeCareProduct
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = self.initial.get('specifications')
        if value is None and self.instance and self.instance.pk:
            value = self.instance.specifications
        if isinstance(value, (dict, list)):
            self.fields['specifications'].initial = json.dumps(value, indent=2, ensure_ascii=False)
        elif value not in (None, ''):
            self.fields['specifications'].initial = value

    def clean_specifications(self):
        raw = self.cleaned_data.get('specifications', '')
        if not raw:
            return {}
        if isinstance(raw, (dict, list)):
            return raw
        text = str(raw).strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {'items': parsed}
            return {'value': parsed}
        except json.JSONDecodeError:
            pass
        parsed_lines = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            sep = ':' if ':' in line else ('=' if '=' in line else None)
            if not sep:
                parsed_lines = {}
                break
            k, v = line.split(sep, 1)
            k, v = k.strip(), v.strip()
            if not k or not v:
                parsed_lines = {}
                break
            parsed_lines[k] = v
        return parsed_lines if parsed_lines else {'value': text}

    def clean_sku(self):
        sku = self.cleaned_data.get('sku', '')
        if sku is None:
            return None
        sku = str(sku).strip()
        return sku or None


class HomeCareProductImageInline(admin.TabularInline):
    model = HomeCareProductImage
    extra = 1
    fields = ['image', 'order']


@admin.register(HomeCareProduct)
class HomeCareProductAdmin(admin.ModelAdmin):
    form = HomeCareProductAdminForm
    inlines = [HomeCareProductImageInline]
    list_display = ['name', 'sku', 'category', 'image_preview', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    list_select_related = ['category']
    autocomplete_fields = ['category']
    fields = ['category', 'name', 'sku', 'description', 'specifications',
              'image', 'external_image_url', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def image_preview(self, obj):
        url = obj.image_url()
        if not url:
            return 'No Image'
        return format_html(
            '<img src="{}" style="height:50px;border-radius:4px;" />',
            url,
        )
    image_preview.short_description = 'Preview'


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Order items are created only through the distributor portal
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = [
        'id', 'distributor_link', 'status_badge', 'item_count',
        'note_excerpt', 'created_at', 'updated_at',
    ]
    list_filter   = ['status', 'created_at', 'distributor']
    search_fields = [
        'distributor__distributor_code', 'distributor__name',
        'distributor__business_name',
    ]
    ordering      = ['-created_at']
    readonly_fields = [
        'distributor', 'created_at', 'updated_at',
    ]
    fields        = ['distributor', 'status', 'note', 'created_at', 'updated_at']
    inlines       = [OrderItemInline]
    actions       = [
        'mark_confirmed', 'mark_fulfilled', 'mark_cancelled',
    ]
    list_select_related = ['distributor']

    # ------------------------------------------------------------------
    # Status transition actions
    # ------------------------------------------------------------------

    def _transition(self, request, queryset, new_status, label):
        updated = 0
        blocked = 0
        for order in queryset:
            if order.can_transition_to(new_status):
                order.status = new_status
                order.save(update_fields=['status', 'updated_at'])
                updated += 1
            else:
                blocked += 1
        if updated:
            self.message_user(
                request,
                f'{updated} order(s) marked as {label}.',
                level=messages.SUCCESS,
            )
        if blocked:
            self.message_user(
                request,
                f'{blocked} order(s) could not be moved to "{label}" '
                f'from their current status.',
                level=messages.WARNING,
            )

    @admin.action(description='Mark selected orders → Confirmed')
    def mark_confirmed(self, request, queryset):
        self._transition(request, queryset, Order.STATUS_CONFIRMED, 'confirmed')

    @admin.action(description='Mark selected orders → Fulfilled')
    def mark_fulfilled(self, request, queryset):
        self._transition(request, queryset, Order.STATUS_FULFILLED, 'fulfilled')

    @admin.action(description='Mark selected orders → Cancelled')
    def mark_cancelled(self, request, queryset):
        self._transition(request, queryset, Order.STATUS_CANCELLED, 'cancelled')

    # ------------------------------------------------------------------
    # Custom change view: also allow inline status change via the form
    # ------------------------------------------------------------------

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None:
            # Limit the status dropdown to valid next states + current state
            allowed = [obj.status] + Order.ALLOWED_TRANSITIONS.get(obj.status, [])
            form.base_fields['status'].choices = [
                (v, l) for v, l in Order.STATUS_CHOICES if v in allowed
            ]
        return form

    def has_add_permission(self, request):
        # Orders are created only through the distributor portal
        return False

    # ------------------------------------------------------------------
    # List display helpers
    # ------------------------------------------------------------------

    @admin.display(description='Distributor', ordering='distributor__distributor_code')
    def distributor_link(self, obj):
        url = reverse('admin:accounts_distributor_change', args=[obj.distributor_id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.distributor,
        )

    _STATUS_COLOURS = {
        Order.STATUS_PENDING:   ('#fef3c7', '#92400e'),
        Order.STATUS_CONFIRMED: ('#dbeafe', '#1e40af'),
        Order.STATUS_FULFILLED: ('#d1fae5', '#065f46'),
        Order.STATUS_CANCELLED: ('#fee2e2', '#991b1b'),
    }

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        bg, fg = self._STATUS_COLOURS.get(obj.status, ('#f1f5f9', '#334155'))
        return format_html(
            '<span style="display:inline-block;padding:2px 10px;border-radius:9999px;'
            'background:{};color:{};font-size:11px;font-weight:600;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.display(description='Items')
    def item_count(self, obj):
        return obj.items.count()

    @admin.display(description='Note')
    def note_excerpt(self, obj):
        if not obj.note:
            return '—'
        return obj.note[:60] + ('…' if len(obj.note) > 60 else '')
