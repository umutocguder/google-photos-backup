# Created by 11hopem (11 Hopem Software Ltd. Şti.)
# Copyright (c) 2026 11hopem. All rights reserved.
# Licensed under 11 Hopem Software Proprietary License.

import unittest
import tempfile
from pathlib import Path
from src.database import DatabaseManager

class TestDatabaseBackup(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_metadata.db"
        self.db = DatabaseManager(self.db_path, auto_backup=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_backup_creation_and_integrity(self):
        # Insert test item
        self.db.save_media_item(
            item_id="test_photo_1",
            filename="photo.jpg",
            mime_type="image/jpeg",
            creation_time="2026-10-02T12:00:00Z",
            file_size=2048,
            sha256="abcdef123456",
            local_path="/tmp/photo.jpg"
        )

        meta = self.db.backup_database()
        self.assertTrue(meta["sha256"])
        self.assertGreater(meta["fileSize"], 0)
        self.assertTrue(self.db.latest_backup_path.exists())
        self.assertTrue(self.db.checksum_log_path.exists())

        is_valid = self.db.verify_backup_integrity()
        self.assertTrue(is_valid)

    def test_restore_from_latest_backup(self):
        self.db.save_media_item(
            item_id="test_photo_2",
            filename="photo2.jpg",
            mime_type="image/jpeg",
            creation_time="2026-10-02T12:00:00Z",
            file_size=4096,
            sha256="987654fedcba",
            local_path="/tmp/photo2.jpg"
        )
        self.db.backup_database()

        restored_size = self.db.restore_from_latest_backup()
        self.assertGreater(restored_size, 0)
        self.assertTrue(self.db.verify_backup_integrity())
        self.assertTrue(self.db.is_item_downloaded("test_photo_2"))

if __name__ == "__main__":
    unittest.main()
