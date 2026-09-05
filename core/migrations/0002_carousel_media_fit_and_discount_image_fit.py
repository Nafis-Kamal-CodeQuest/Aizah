"""Add per-slide media_fit (CarouselAd) and image_fit (DiscountAnnouncement).

This gives the admin explicit, intentional control over how each uploaded
asset should fit its container — cover (full-bleed crop) or contain (full
image, no crop). Previously the fit was hard-coded in the template, which
made portrait uploads look broken inside the landscape hero.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='carouselad',
            name='media_fit',
            field=models.CharField(
                choices=[
                    ('cover', 'Cover — fill the hero, crop if needed (best for landscape)'),
                    ('contain', 'Contain — show the entire image with no crop (best for portrait)'),
                ],
                default='cover',
                help_text=(
                    'How the media should fit inside the hero. Use "cover" for '
                    'landscape images/videos (full-bleed). Use "contain" for '
                    'portrait images so the whole artwork stays visible.'
                ),
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='discountannouncement',
            name='image_fit',
            field=models.CharField(
                choices=[
                    ('cover', 'Cover — image fills the card, crop allowed (typical promo look)'),
                    ('contain', 'Contain — entire image visible, no crop'),
                ],
                default='cover',
                help_text=(
                    'How the promo image fits the card. "cover" fills the card '
                    '(typical marketing look, may crop). "contain" preserves the '
                    'whole image with no crop.'
                ),
                max_length=10,
            ),
        ),
    ]
