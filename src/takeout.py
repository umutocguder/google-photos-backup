import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import config
from src.database import DatabaseManager

MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".raw", ".dng",
    ".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp"
}

class TakeoutImporter:
    """Imports and reconciles Google Takeout export archives with local database."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        target_dir: Optional[Path] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.target_dir = target_dir or (config.downloads_dir / "Takeout")

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _find_sidecar_json(self, media_file: Path) -> Optional[Path]:
        """Look for companion Google Takeout metadata JSON file."""
        # Standard: photo.jpg.json
        candidate1 = media_file.parent / f"{media_file.name}.json"
        if candidate1.exists():
            return candidate1

        # Alternative: photo.json
        candidate2 = media_file.parent / f"{media_file.stem}.json"
        if candidate2.exists():
            return candidate2

        return None

    def scan_and_import(self, source_path: Path, copy_files: bool = True) -> Dict[str, Any]:
        """
        Scan a Google Takeout folder and index/import media items into backup.
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Takeout path does not exist: {source}")

        summary = {
            "scanned": 0,
            "imported": 0,
            "deduplicated": 0,
            "errors": 0,
        }

        self.target_dir.mkdir(parents=True, exist_ok=True)

        for root, _, files in os.walk(source):
            for file in files:
                file_path = Path(root) / file
                suffix = file_path.suffix.lower()

                if suffix not in MEDIA_EXTENSIONS:
                    continue

                summary["scanned"] += 1
                try:
                    file_hash = self._compute_hash(file_path)
                    existing_path = self.db.has_file_hash(file_hash)

                    if existing_path and Path(existing_path).exists():
                        summary["deduplicated"] += 1
                        continue

                    # Extract metadata from companion JSON if available
                    creation_time_str = None
                    sidecar = self._find_sidecar_json(file_path)
                    if sidecar:
                        try:
                            with open(sidecar, "r", encoding="utf-8") as jf:
                                meta = json.load(jf)
                                ts = meta.get("photoTakenTime", {}).get("timestamp")
                                if ts:
                                    creation_time_str = datetime.utcfromtimestamp(int(ts)).isoformat()
                        except Exception:
                            pass

                    # Determine target path
                    year = "Takeout_Archive"
                    month = "All"
                    if creation_time_str:
                        try:
                            dt = datetime.fromisoformat(creation_time_str)
                            year = dt.strftime("%Y")
                            month = dt.strftime("%m")
                        except Exception:
                            pass

                    dest_dir = self.target_dir / year / month
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = dest_dir / file_path.name

                    if copy_files:
                        shutil.copy2(file_path, dest_file)
                    else:
                        dest_file = file_path

                    # Preserve timestamp
                    if creation_time_str:
                        dt = datetime.fromisoformat(creation_time_str)
                        os.utime(dest_file, (dt.timestamp(), dt.timestamp()))

                    # Save to DB
                    synthetic_id = f"takeout_{file_hash[:16]}"
                    file_size = dest_file.stat().st_size
                    mime = "video/" if suffix in {".mp4", ".mov", ".avi"} else "image/"

                    self.db.save_media_item(
                        item_id=synthetic_id,
                        filename=dest_file.name,
                        mime_type=f"{mime}{suffix.replace('.', '')}",
                        creation_time=creation_time_str,
                        file_size=file_size,
                        sha256=file_hash,
                        local_path=str(dest_file),
                        album_title="Google Takeout Import",
                    )
                    summary["imported"] += 1

                except Exception as e:
                    summary["errors"] += 1

        return summary
