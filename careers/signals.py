"""
careers/signals.py
------------------
Fires a background thread to sync a new JobApplication to Google Sheets
immediately after it is saved for the first time.

Design choices:
  - Uses post_save with `created=True` guard so edits/updates are ignored.
  - Runs the sheet call in a daemon thread so the HTTP response is never
    held up by a slow network or API quota wait.
  - On success  → sets application.synced_to_sheet = True (DB update).
  - On failure  → logs the error; synced_to_sheet stays False so the
    management command `retry_sheet_sync` can pick it up later.
  - The application is always saved to the DB regardless of sheet outcome.
"""

import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import JobApplication
from .sheets import append_application

logger = logging.getLogger(__name__)


def _sync_in_background(application_pk: int) -> None:
    """Worker function executed in a daemon thread."""
    # Re-fetch from DB inside the thread to avoid cross-thread ORM issues.
    try:
        from .models import JobApplication as _App  # local import avoids circular refs
        application = _App.objects.select_related('job').get(pk=application_pk)
    except _App.DoesNotExist:
        logger.warning('sheets: application pk=%s not found in thread — skipping', application_pk)
        return

    success = append_application(application)

    if success:
        # Only update the single field to avoid stomping concurrent changes.
        _App.objects.filter(pk=application_pk).update(synced_to_sheet=True)
        logger.info('sheets: marked application pk=%s as synced', application_pk)
    else:
        logger.warning(
            'sheets: sync failed for application pk=%s — '
            'will be retried by `manage.py retry_sheet_sync`',
            application_pk,
        )


@receiver(post_save, sender=JobApplication)
def on_application_created(sender, instance, created, **kwargs):
    """Trigger a background sheet sync only when a new application is created."""
    if not created:
        return  # ignore status updates, admin edits, etc.

    thread = threading.Thread(
        target=_sync_in_background,
        args=(instance.pk,),
        daemon=True,   # won't block process shutdown
        name=f'sheet-sync-{instance.pk}',
    )
    thread.start()
    logger.debug('sheets: started background sync thread for application pk=%s', instance.pk)
