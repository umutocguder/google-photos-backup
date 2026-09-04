# Created by 11hopem (11 Hopem Software Ltd. Şti.)
# Copyright (c) 2026 11hopem. All rights reserved.
# Licensed under 11 Hopem Software Proprietary License.

import sqlite3
from datetime import datetime, timezone

from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import config

class DatabaseManager:
    """Manages SQLite storage for tracking media metadata, checksums, and sync history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS media_items (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    mime_type TEXT,
                    creation_time TEXT,
                    file_size INTEGER DEFAULT 0,
                    sha256 TEXT,
                    local_path TEXT,
                    album_id TEXT,
                    album_title TEXT,
                    downloaded_at TEXT NOT NULL,
                    status TEXT DEFAULT 'completed'
                );

                CREATE INDEX IF NOT EXISTS idx_media_sha256 ON media_items(sha256);
                CREATE INDEX IF NOT EXISTS idx_media_creation ON media_items(creation_time);

                CREATE TABLE IF NOT EXISTS albums (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    total_media_items INTEGER DEFAULT 0,
                    cover_photo_url TEXT,
                    last_synced_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    items_scanned INTEGER DEFAULT 0,
                    items_downloaded INTEGER DEFAULT 0,
                    bytes_downloaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    error_message TEXT
                );
            """)
            conn.commit()

    def is_item_downloaded(self, item_id: str) -> bool:
        """Check if a Google Photos media item ID has already been recorded."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM media_items WHERE id = ? LIMIT 1", (item_id,))
            return cursor.fetchone() is not None

    def has_file_hash(self, sha256: str) -> Optional[str]:
        """Check if a file with the identical SHA-256 hash already exists locally."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT local_path FROM media_items WHERE sha256 = ? LIMIT 1", (sha256,))
            row = cursor.fetchone()
            return row["local_path"] if row else None

    def save_media_item(
        self,
        item_id: str,
        filename: str,
        mime_type: Optional[str],
        creation_time: Optional[str],
        file_size: int,
        sha256: str,
        local_path: str,
        album_id: Optional[str] = None,
        album_title: Optional[str] = None,
    ) -> None:
        """Insert or replace a downloaded media item record."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO media_items (
                    id, filename, mime_type, creation_time, file_size,
                    sha256, local_path, album_id, album_title, downloaded_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                (
                    item_id,
                    filename,
                    mime_type,
                    creation_time,
                    file_size,
                    sha256,
                    local_path,
                    album_id,
                    album_title,
                    now,
                ),
            )
            conn.commit()

    def save_album(self, album_id: str, title: str, total_items: int, cover_url: Optional[str] = None) -> None:
        """Insert or update album metadata."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO albums (id, title, total_media_items, cover_photo_url, last_synced_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (album_id, title, total_items, cover_url, now),
            )
            conn.commit()

    def start_sync_run(self) -> int:
        """Create a new sync run log entry and return its ID."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sync_runs (started_at, status) VALUES (?, 'running')",
                (now,),
            )
            conn.commit()
            return cursor.lastrowid

    def finish_sync_run(
        self,
        run_id: int,
        items_scanned: int,
        items_downloaded: int,
        bytes_downloaded: int,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> None:
        """Mark a sync run as finished with summary metrics."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sync_runs
                SET completed_at = ?, items_scanned = ?, items_downloaded = ?,
                    bytes_downloaded = ?, status = ?, error_message = ?
                WHERE id = ?
                """,
                (now, items_scanned, items_downloaded, bytes_downloaded, status, error, run_id),
            )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate summary statistics for CLI and web dashboards."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM media_items")
            total_items, total_bytes = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) FROM media_items WHERE mime_type LIKE 'image/%'")
            total_photos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM media_items WHERE mime_type LIKE 'video/%'")
            total_videos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM albums")
            total_albums = cursor.fetchone()[0]

            cursor.execute("SELECT * FROM sync_runs ORDER BY id DESC LIMIT 5")
            recent_runs = [dict(row) for row in cursor.fetchall()]

            return {
                "total_items": total_items,
                "total_photos": total_photos,
                "total_videos": total_videos,
                "total_bytes": total_bytes,
                "total_albums": total_albums,
                "recent_runs": recent_runs,
            }

    def get_recent_items(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve most recently downloaded media items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM media_items ORDER BY downloaded_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_albums(self) -> List[Dict[str, Any]]:
        """List tracked albums."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM albums ORDER BY title ASC")
            return [dict(row) for row in cursor.fetchall()]
