"""
Management command: retry_sheet_sync
--------------------------------------
Retries Google Sheets sync for all JobApplications where
synced_to_sheet=False.

Usage:
    python manage.py retry_sheet_sync
    python manage.py retry_sheet_sync --limit 50
    python manage.py retry_sheet_sync --dry-run

Typical use: run from a cron job or after fixing credentials.

cPanel cron example (every hour):
    0 * * * * /path/to/venv/bin/python /path/to/manage.py retry_sheet_sync >> /tmp/sheet_sync.log 2>&1
"""

from django.core.management.base import BaseCommand

from careers.models import JobApplication
from careers.sheets import append_application


class Command(BaseCommand):
    help = 'Retry Google Sheets sync for all unsynced job applications.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maximum number of applications to process in this run (0 = no limit).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List unsynced applications without actually syncing them.',
        )

    def handle(self, *args, **options):
        limit   = options['limit']
        dry_run = options['dry_run']

        qs = (
            JobApplication.objects
            .filter(synced_to_sheet=False)
            .select_related('job')
            .order_by('applied_at')
        )
        if limit:
            qs = qs[:limit]

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('All applications are already synced. Nothing to do.'))
            return

        self.stdout.write(f'Found {total} unsynced application(s).')

        if dry_run:
            for app in qs:
                self.stdout.write(
                    f'  [dry-run] pk={app.pk}  {app.full_name}  <{app.email}>  '
                    f'→ {app.job.title}  applied={app.applied_at:%Y-%m-%d %H:%M}'
                )
            self.stdout.write(self.style.WARNING('Dry run complete — no rows written.'))
            return

        synced = 0
        failed = 0

        for app in qs:
            success = append_application(app)
            if success:
                JobApplication.objects.filter(pk=app.pk).update(synced_to_sheet=True)
                synced += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Synced pk={app.pk} — {app.full_name}')
                )
            else:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed pk={app.pk} — {app.full_name}')
                )

        self.stdout.write(
            f'\nDone: {synced} synced, {failed} failed '
            f'(check logs for details on failures).'
        )
