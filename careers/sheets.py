"""
careers/sheets.py
-----------------
Thin wrapper around gspread for appending JobApplication rows to a
Google Sheet.

Environment variables consumed (loaded via settings.py):
  GOOGLE_SERVICE_ACCOUNT_JSON  — absolute path to the service-account
                                  key file  (preferred), OR the raw JSON
                                  string (useful for env-var-only hosts).
  GOOGLE_SHEET_ID              — the spreadsheet ID from the sheet URL.

Public API used by signals.py:
  append_application(application)  →  True on success, False on failure.

Thread-safety:
  All writes go through _SHEET_LOCK so concurrent background threads
  (e.g. two applicants submitting at the same moment) never interleave
  their header-check + append sequence.
"""

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

# Module-level lock — serialises all writes regardless of which thread
# calls append_application().
_SHEET_LOCK = threading.Lock()

# Column headers written to A1 when that cell is empty.
SHEET_HEADERS = [
    'Applied At',
    'Full Name',
    'Email',
    'Phone',
    'Job Role',
    'Department',
    'Employment Type',
    'Resume URL',
    'Cover Letter',
    'Status',
    'Application ID',
]


# ---------------------------------------------------------------------------
# Auth / client helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Return an authorised gspread client, or raise if credentials are missing."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
    ]

    raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip()
    if not raw:
        raise EnvironmentError(
            'GOOGLE_SERVICE_ACCOUNT_JSON is not set. '
            'Set it to the path of your service-account key file, '
            'or to the raw JSON string.'
        )

    if raw.startswith('{'):
        # Inline JSON string (useful on hosts that only allow env vars)
        info = json.loads(raw)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        # File path
        if not os.path.isfile(raw):
            raise FileNotFoundError(
                f'Service account key file not found: {raw!r}. '
                'Check GOOGLE_SERVICE_ACCOUNT_JSON.'
            )
        creds = Credentials.from_service_account_file(raw, scopes=scopes)

    return gspread.authorize(creds)


def _get_sheet():
    """Return the first worksheet of the configured spreadsheet."""
    sheet_id = os.environ.get('GOOGLE_SHEET_ID', '').strip()
    if not sheet_id:
        raise EnvironmentError(
            'GOOGLE_SHEET_ID is not set. '
            'Copy it from the Google Sheets URL and add it to your .env.'
        )
    client = _get_client()
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.sheet1


# ---------------------------------------------------------------------------
# Header + formatting helpers
# ---------------------------------------------------------------------------

def _ensure_header(worksheet):
    """
    Write the header row to A1 explicitly if A1 is empty.

    Uses sheet.update() rather than append_row() so the header is
    guaranteed to land at A1 and never drifts to an unexpected row.

    Also applies one-time formatting:
      - Freeze row 1 so the header stays visible while scrolling.
      - Set wrap strategy to CLIP on A:Z so long cells don't blow up
        row height.

    Must be called inside _SHEET_LOCK.
    """
    # Check A1 only — a single cell read is cheap and avoids fetching
    # the entire sheet on every sync.
    a1_value = worksheet.acell('A1').value
    if a1_value:
        return  # header already present

    # Write header to A1 explicitly.
    worksheet.update(
        range_name='A1',
        values=[SHEET_HEADERS],
        value_input_option='RAW',
    )
    logger.info('sheets: wrote header row to A1')

    # Freeze row 1.
    worksheet.freeze(rows=1)

    # Clip long text so rows stay a single line tall.
    worksheet.format('A:Z', {'wrapStrategy': 'CLIP'})
    logger.info('sheets: applied freeze + CLIP wrap formatting')


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def _clean(text):
    """Replace newlines / carriage-returns with a space to keep cells single-line."""
    if not text:
        return ''
    return str(text).replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()


def _build_row(application):
    """Return a flat list of cell values for one JobApplication row."""
    resume_url = ''
    if application.resume:
        try:
            from django.conf import settings as django_settings
            base = getattr(django_settings, 'SITE_URL', '').rstrip('/')
            resume_url = base + application.resume.url
        except Exception:
            resume_url = str(application.resume)

    applied_at = (
        application.applied_at.strftime('%Y-%m-%d %H:%M:%S')
        if application.applied_at
        else ''
    )

    return [
        applied_at,
        _clean(application.full_name),
        _clean(application.email),
        _clean(application.phone),
        _clean(application.job.title),
        _clean(application.job.get_department_display()),
        _clean(application.job.get_employment_type_display()),
        resume_url,
        _clean(application.cover_letter),   # multi-line field — newlines stripped
        _clean(application.get_status_display()),
        str(application.pk),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def append_application(application):
    """
    Append *application* as a new row in the configured Google Sheet.

    Returns True on success, False on any failure.
    Never raises — callers must not let sheet errors affect the user flow.

    Thread-safe: acquires _SHEET_LOCK so concurrent calls don't race on
    the header check or produce offset rows.
    """
    try:
        with _SHEET_LOCK:
            worksheet = _get_sheet()
            _ensure_header(worksheet)
            row = _build_row(application)
            # table_range="A1" anchors the append to column A regardless of
            # where the API thinks the "table" ends, preventing column offset.
            worksheet.append_row(
                row,
                value_input_option='USER_ENTERED',
                table_range='A1',
            )
        logger.info(
            'sheets: appended application pk=%s (%s) to sheet',
            application.pk, application.full_name,
        )
        return True
    except EnvironmentError as exc:
        logger.error('sheets: configuration error — %s', exc)
    except FileNotFoundError as exc:
        logger.error('sheets: credential file error — %s', exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            'sheets: unexpected error appending application pk=%s — %s',
            getattr(application, 'pk', '?'), exc,
        )
    return False
