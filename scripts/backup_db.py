# Created by 11hopem (11 Hopem Software Ltd. Şti.)
# Copyright (c) 2026 11hopem. All rights reserved.
# Licensed under 11 Hopem Software Proprietary License.

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.database import DatabaseManager

def main():
    try:
        db = DatabaseManager(auto_backup=False)
        meta = db.backup_database()
        valid = db.verify_backup_integrity()
        print(f"[Google Photos DB Backup Success] File: {meta['backupFile']}, Size: {meta['fileSize']} bytes, Verified: {valid}")
    except Exception as e:
        print(f"[Google Photos DB Backup Error]: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
