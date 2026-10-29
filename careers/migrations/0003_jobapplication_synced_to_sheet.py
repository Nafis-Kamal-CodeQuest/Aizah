from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('careers', '0002_careerpagesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobapplication',
            name='synced_to_sheet',
            field=models.BooleanField(
                default=False,
                help_text='Set to True once this application has been successfully appended to Google Sheets.',
            ),
        ),
    ]
