from mimetypes import guess_type

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


ALLOWED_MEDIA_EXTENSIONS = {
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif', '.tiff', '.tif',
    # Video
    '.mp4', '.webm', '.mov', '.m4v', '.ogv', '.mkv', '.avi',
}


def _validate_media_file(value):
    """Only allow image and video file types on CarouselAd.media_file."""
    if not value or not hasattr(value, 'name'):
        return
    name = value.name.lower()
    from pathlib import Path
    ext = Path(name).suffix
    if ext not in ALLOWED_MEDIA_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS))
        raise ValidationError(
            f'File extension "{ext}" is not allowed. '
            f'Allowed extensions: {allowed}'
        )


class Category(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=20, unique=True, blank=True, null=True)
    description = models.TextField()
    specifications = models.JSONField(blank=True, default=dict)
    image = models.ImageField(upload_to='products', blank=True)
    external_image_url = models.URLField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Products'

    def image_url(self):
        if self.external_image_url:
            return self.external_image_url
        if self.image:
            return self.image.url
        return ''

    def __str__(self):
        return self.name


class CarouselAd(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    MEDIA_FIT_CHOICES = [
        ('cover', 'Cover — fill the hero, crop if needed (best for landscape)'),
        ('contain', 'Contain — show the entire image with no crop (best for portrait)'),
    ]

    title = models.CharField(max_length=300, blank=True, default='')
    subtitle = models.TextField(blank=True, default='')
    cta_text = models.CharField(max_length=100, blank=True, default='Explore')
    cta_href = models.CharField(max_length=200, blank=True, default='#products')
    tag = models.CharField(max_length=100, blank=True, default='')
    media_file = models.FileField(upload_to='carousel-media/', blank=True, validators=[_validate_media_file])
    external_image_url = models.URLField(blank=True)
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPE_CHOICES, default='image')
    media_fit = models.CharField(
        max_length=10,
        choices=MEDIA_FIT_CHOICES,
        default='cover',
        help_text=(
            'How the media should fit inside the hero. Use "cover" for '
            'landscape images/videos (full-bleed). Use "contain" for portrait '
            'images so the whole artwork stays visible.'
        ),
    )
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def image_url(self):
        if self.external_image_url:
            return self.external_image_url
        if self.media_file:
            return self.media_file.url
        return ''

    def media_url(self):
        return self.image_url()

    def resolved_media_type(self):
        source_name = ''
        if self.media_file:
            source_name = self.media_file.name
        elif self.external_image_url:
            source_name = self.external_image_url

        guessed_type, _ = guess_type(source_name)
        if guessed_type:
            return 'video' if guessed_type.startswith('video/') else 'image'

        if source_name.lower().endswith(('.mp4', '.webm', '.mov', '.m4v', '.ogv')):
            return 'video'

        return self.media_type or 'image'

    def __str__(self):
        return f"Ad #{self.pk} ({self.media_type})"


class DiscountAnnouncement(models.Model):
    IMAGE_FIT_CHOICES = [
        ('cover', 'Cover — image fills the card, crop allowed (typical promo look)'),
        ('contain', 'Contain — entire image visible, no crop'),
    ]

    title = models.CharField(max_length=300, blank=True, default='')
    description = models.TextField(blank=True, default='')
    badge = models.CharField(max_length=100, blank=True, default='Active Offer')
    badge_tone = models.CharField(
        max_length=20,
        choices=[('brand', 'brand'), ('amber', 'amber')],
        default='brand'
    )
    image = models.ImageField(upload_to='announcements/', blank=True)
    external_image_url = models.URLField(blank=True)
    image_fit = models.CharField(
        max_length=10,
        choices=IMAGE_FIT_CHOICES,
        default='cover',
        help_text=(
            'How the promo image fits the card. "cover" fills the card '
            '(typical marketing look, may crop). "contain" preserves the '
            'whole image with no crop.'
        ),
    )
    meta_text = models.CharField(max_length=200, blank=True, default='')
    order = models.PositiveIntegerField(
        default=0,
        help_text='Controls slide order in the carousel. Lower numbers appear first.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Discount Announcement'
        verbose_name_plural = 'Discount Announcements'

    def image_url(self):
        if self.external_image_url:
            return self.external_image_url
        if self.image:
            return self.image.url
        return ''

    def __str__(self):
        return f"Discount Announcement #{self.pk} ({self.created_at})"


class CompanyInfo(models.Model):
    mission = models.TextField()
    vision = models.TextField()
    values = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.pk is None and CompanyInfo.objects.exists():
            raise ValidationError('CompanyInfo already exists')

    def save(self, *args, **kwargs):
        if self.pk is None and CompanyInfo.objects.exists():
            raise ValidationError('CompanyInfo already exists')
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Company Information'


class ContactInfo(models.Model):
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    social_media_links = models.JSONField(blank=True, default=list)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.pk is None and ContactInfo.objects.exists():
            raise ValidationError('ContactInfo already exists')

    def save(self, *args, **kwargs):
        if self.pk is None and ContactInfo.objects.exists():
            raise ValidationError('ContactInfo already exists')
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Company Contact Info'


class Order(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_FULFILLED = 'fulfilled'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_FULFILLED, 'Fulfilled'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    # Legal next-statuses for each current status (admin-side transitions)
    ALLOWED_TRANSITIONS = {
        STATUS_PENDING:   [STATUS_CONFIRMED, STATUS_CANCELLED],
        STATUS_CONFIRMED: [STATUS_FULFILLED, STATUS_CANCELLED],
        STATUS_FULFILLED: [],
        STATUS_CANCELLED: [],
    }

    # FK to Distributor — PROTECT so deleting a distributor is blocked when
    # they have order history.  The accounts app is imported lazily via the
    # string reference to avoid a circular import at module load time.
    distributor = models.ForeignKey(
        'accounts.Distributor',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    note = models.TextField(
        blank=True,
        default='',
        help_text='Optional delivery preference or note from the distributor.',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f'Order #{self.pk} — {self.distributor.distributor_code} ({self.status})'

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    # No price field — quantity only, matching the public site's no-pricing model.
    quantity = models.PositiveIntegerField()

    class Meta:
        # Each product appears at most once per order
        unique_together = [('order', 'product')]
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f'{self.product.name} × {self.quantity} (Order #{self.order_id})'


class HomeCareCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Home Care Category'
        verbose_name_plural = 'Home Care Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while HomeCareCategory.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HomeCareProduct(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=20, unique=True, blank=True, null=True)
    description = models.TextField()
    specifications = models.JSONField(blank=True, default=dict)
    image = models.ImageField(upload_to='homecare-products/', blank=True)
    external_image_url = models.URLField(blank=True)
    category = models.ForeignKey(
        HomeCareCategory,
        on_delete=models.PROTECT,
        related_name='products',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Home Care Product'
        verbose_name_plural = 'Home Care Products'

    def image_url(self):
        if self.external_image_url:
            return self.external_image_url
        if self.image:
            return self.image.url
        return ''

    def __str__(self):
        return self.name


class ContactInquiry(models.Model):
    PRODUCT_INTEREST_CHOICES = [
        ('Chanachur & Snacks', 'Chanachur & Snacks'),
        ('Bottled Water', 'Bottled Water'),
        ('Hygiene Products', 'Hygiene Products'),
        ('Full Catalog', 'Full Catalog'),
        ('Private Label / OEM', 'Private Label / OEM'),
    ]

    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True, default='')
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, default='')
    product_interest = models.CharField(max_length=100, choices=PRODUCT_INTEREST_CHOICES, blank=True, default='')
    message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Inquiry'
        verbose_name_plural = 'Contact Inquiries'

    def __str__(self):
        return f"Inquiry from {self.name} ({self.email})"
