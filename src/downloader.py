import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import requests
from src.config import config
from src.database import DatabaseManager

class MediaDownloader:
    """Concurrent, resumable media downloader with EXIF timestamp and deduplication support."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        downloads_dir: Optional[Path] = None,
        max_workers: int = 5,
        organize_by: str = "date",
    ):
        self.db = db_manager or DatabaseManager()
        self.downloads_dir = downloads_dir or config.downloads_dir
        self.max_workers = max_workers
        self.organize_by = organize_by

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal or invalid characters."""
        clean = re.sub(r'[\\/*?:"<>|]', "_", filename)
        return clean.strip() or "unnamed_media"

    def _determine_target_path(
        self,
        filename: str,
        creation_time_str: Optional[str],
        album_title: Optional[str] = None,
    ) -> Path:
        """Calculate directory tree path based on date or album organization."""
        clean_filename = self._sanitize_filename(filename)

        if self.organize_by == "album" and album_title:
            clean_album = self._sanitize_filename(album_title)
            dest_dir = self.downloads_dir / "Albums" / clean_album
        else:
            # Default: YYYY/MM structure
            year = "Unknown_Year"
            month = "Unknown_Month"
            if creation_time_str:
                try:
                    dt = datetime.fromisoformat(creation_time_str.replace("Z", "+00:00"))
                    year = dt.strftime("%Y")
                    month = dt.strftime("%m")
                except Exception:
                    pass
            dest_dir = self.downloads_dir / year / month

        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / clean_filename

        # Avoid filename collisions
        counter = 1
        stem = target.stem
        suffix = target.suffix
        while target.exists():
            target = dest_dir / f"{stem} ({counter}){suffix}"
            counter += 1

        return target

    def _apply_file_timestamp(self, file_path: Path, creation_time_str: Optional[str]) -> None:
        """Set filesystem access and modification timestamps to match original capture time."""
        if not creation_time_str:
            return
        try:
            dt = datetime.fromisoformat(creation_time_str.replace("Z", "+00:00"))
            epoch_time = dt.timestamp()
            os.utime(file_path, (epoch_time, epoch_time))
        except Exception:
            pass

    def download_item(
        self,
        item: Dict[str, Any],
        album_id: Optional[str] = None,
        album_title: Optional[str] = None,
    ) -> Tuple[bool, str, int]:
        """
        Download a single Google Photos item.
        Returns: (success: bool, status_message: str, bytes_downloaded: int)
        """
        item_id = item["id"]
        filename = item.get("filename", f"photo_{item_id}.jpg")
        mime_type = item.get("mimeType", "")
        base_url = item.get("baseUrl", "")
        metadata = item.get("mediaMetadata", {})
        creation_time = metadata.get("creationTime")

        # 1. Skip if already processed by ID
        if self.db.is_item_downloaded(item_id):
            return True, "already_downloaded", 0

        # 2. Append download flag (=d for original photo, =dv for original video)
        is_video = mime_type.startswith("video/") or "video" in metadata
        download_url = f"{base_url}=dv" if is_video else f"{base_url}=d"

        target_path = self._determine_target_path(filename, creation_time, album_title)
        temp_path = target_path.with_suffix(f".tmp_{item_id[:8]}")

        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            with requests.get(download_url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
                            total_bytes += len(chunk)

            file_hash = hasher.hexdigest()

            # 3. Check for existing identical file by SHA-256 hash
            existing_path = self.db.has_file_hash(file_hash)
            if existing_path and Path(existing_path).exists():
                temp_path.unlink(missing_ok=True)
                # Register reference in DB without storing redundant copy
                self.db.save_media_item(
                    item_id=item_id,
                    filename=filename,
                    mime_type=mime_type,
                    creation_time=creation_time,
                    file_size=total_bytes,
                    sha256=file_hash,
                    local_path=existing_path,
                    album_id=album_id,
                    album_title=album_title,
                )
                return True, "deduplicated", 0

            # 4. Finalize file
            temp_path.rename(target_path)
            self._apply_file_timestamp(target_path, creation_time)

            # 5. Record to database
            self.db.save_media_item(
                item_id=item_id,
                filename=filename,
                mime_type=mime_type,
                creation_time=creation_time,
                file_size=total_bytes,
                sha256=file_hash,
                local_path=str(target_path),
                album_id=album_id,
                album_title=album_title,
            )
            return True, "downloaded", total_bytes

        except Exception as e:
            temp_path.unlink(missing_ok=True)
            return False, f"error: {str(e)}", 0

    def download_batch_concurrent(
        self,
        items: list,
        album_id: Optional[str] = None,
        album_title: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Download a batch of media items concurrently using a thread pool."""
        results = {
            "total": len(items),
            "downloaded": 0,
            "deduplicated": 0,
            "skipped": 0,
            "failed": 0,
            "bytes": 0,
        }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {
                executor.submit(self.download_item, item, album_id, album_title): item
                for item in items
            }

            completed_count = 0
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                completed_count += 1
                try:
                    success, status, nbytes = future.result()
                    if success:
                        if status == "downloaded":
                            results["downloaded"] += 1
                            results["bytes"] += nbytes
                        elif status == "deduplicated":
                            results["deduplicated"] += 1
                        elif status == "already_downloaded":
                            results["skipped"] += 1
                    else:
                        results["failed"] += 1

                    if progress_callback:
                        progress_callback(completed_count, len(items), item.get("filename", ""))
                except Exception:
                    results["failed"] += 1

        return results
