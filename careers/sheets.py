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
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Column headers written to row 1 when the sheet is empty.
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


def _get_client():
    """Return an authorised gspread client, or raise if credentials are missing."""
    # Import here so the module can be imported without gspread installed
    # (ImportError surfaces only when the function is actually called).
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

    # Decide: is it a file path or a JSON blob?
    if raw.startswith('{'):
        # Inline JSON string (common on PaaS / cPanel env-var panels)
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


def _ensure_header(worksheet):
    """Write the header row if the sheet is empty (no existing rows)."""
    existing = worksheet.get_all_values()
    if not existing:
        worksheet.append_row(SHEET_HEADERS, value_input_option='RAW')


def _build_row(application):
    """Return a list of cell values for one JobApplication row."""
    # Resume URL: build an absolute URL when possible; fall back to the
    # raw field name so the row is still useful.
    resume_url = ''
    if application.resume:
        try:
            from django.conf import settings as django_settings
            base = (
                getattr(django_settings, 'SITE_URL', '').rstrip('/')
                or ''
            )
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
        application.full_name,
        application.email,
        application.phone,
        application.job.title,
        application.job.get_department_display(),
        application.job.get_employment_type_display(),
        resume_url,
        application.cover_letter,
        application.get_status_display(),
        str(application.pk),
    ]


def append_application(application):
    """
    Append *application* as a new row in the configured Google Sheet.

    Returns True on success, False on any failure.
    Never raises — callers must not let sheet errors affect the user flow.
    """
    try:
        worksheet = _get_sheet()
        _ensure_header(worksheet)
        row = _build_row(application)
        worksheet.append_row(row, value_input_option='USER_ENTERED')
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
