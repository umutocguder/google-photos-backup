# Created by 11Hopem
# Copyright (c) 2026 11hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

import os
from dataclasses import dataclass
from pathlib import Path


# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class AppConfig:
    """Application configuration and file system paths."""
    base_dir: Path = BASE_DIR
    storage_dir: Path = BASE_DIR / "storage"
    downloads_dir: Path = BASE_DIR / "downloads"
    db_path: Path = BASE_DIR / "storage" / "metadata.db"
    credentials_path: Path = BASE_DIR / "credentials.json"
    token_path: Path = BASE_DIR / "token.json"
    
    # Download & Sync Defaults
    max_workers: int = 5
    batch_size: int = 100
    organize_by: str = "date"  # "date" (YYYY/MM) or "album" (Albums/<name>)
    download_videos: bool = True
    preserve_exif_time: bool = True
    web_host: str = "127.0.0.1"
    web_port: int = 8080

    def ensure_directories(self) -> None:
        """Ensure necessary runtime directories exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

# Global configuration singleton
config = AppConfig()
config.ensure_directories()
