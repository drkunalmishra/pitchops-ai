"""Cloud Storage helpers. The bucket holds only rendered output and owned assets."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import storage  # type: ignore[attr-defined]

from pitchops.config import get_settings


@lru_cache
def bucket() -> storage.Bucket:
    s = get_settings()
    return storage.Client(project=s.gcp_project_id).bucket(s.bucket)


def upload_bytes(path: str, data: bytes, content_type: str) -> str:
    blob = bucket().blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket().name}/{path}"
