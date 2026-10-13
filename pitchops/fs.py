"""Firestore client (named database from settings)."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import firestore

from pitchops.config import get_settings


@lru_cache
def client() -> firestore.Client:
    s = get_settings()
    return firestore.Client(project=s.gcp_project_id, database=s.firestore_database)
