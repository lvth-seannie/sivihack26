"""Thin wrapper around Django's storage API, backed by Backblaze B2
(S3-compatible, configured in settings.py). Feature code should import
from here rather than calling django.core.files.storage directly, so the
backend can be swapped without touching callers.
"""

from django.core.files.storage import default_storage


def upload_file(file_obj, path: str) -> str:
    """Uploads a file-like object to B2 and returns its URL."""
    saved_path = default_storage.save(path, file_obj)
    return default_storage.url(saved_path)


def delete_file(path: str) -> None:
    if default_storage.exists(path):
        default_storage.delete(path)


def file_exists(path: str) -> bool:
    return default_storage.exists(path)


def file_url(path: str) -> str:
    """Returns the URL for an already-stored file without re-uploading it."""
    return default_storage.url(path)


def download_file(path: str) -> bytes:
    """Reads a stored file back into memory (e.g. for extraction to read a
    previously-cached PDF)."""
    with default_storage.open(path, "rb") as f:
        return f.read()
