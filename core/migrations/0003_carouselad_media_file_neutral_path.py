from pathlib import Path
import os

from django.conf import settings
from django.db import migrations, models


OLD_PREFIX = ''.join(['ad', 's/'])
NEW_PREFIX = 'carousel-media/'


def _move_media_paths(apps, schema_editor, source_prefix, target_prefix):
    CarouselAd = apps.get_model('core', 'CarouselAd')
    media_root = Path(settings.MEDIA_ROOT)

    for slide in CarouselAd.objects.filter(media_file__startswith=source_prefix):
        old_name = slide.media_file.name
        if not old_name.startswith(source_prefix):
            continue

        new_name = target_prefix + old_name[len(source_prefix):]
        source_path = media_root / old_name
        target_path = media_root / new_name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if source_path.exists():
            os.replace(source_path, target_path)
        elif not target_path.exists():
            continue

        CarouselAd.objects.filter(pk=slide.pk).update(media_file=new_name)


def forwards(apps, schema_editor):
    _move_media_paths(apps, schema_editor, OLD_PREFIX, NEW_PREFIX)


def backwards(apps, schema_editor):
    _move_media_paths(apps, schema_editor, NEW_PREFIX, OLD_PREFIX)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_carousel_media_fit_and_discount_image_fit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carouselad',
            name='media_file',
            field=models.FileField(blank=True, upload_to='carousel-media/'),
        ),
        migrations.RunPython(forwards, reverse_code=backwards),
    ]
