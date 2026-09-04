import tempfile
import unittest
from pathlib import Path
from src.database import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    """Unit tests for SQLite database operations and deduplication logic."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_metadata.db"
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        """Test that all tables and indices are created properly."""
        self.assertTrue(self.db_path.exists())
        stats = self.db.get_stats()
        self.assertEqual(stats["total_items"], 0)
        self.assertEqual(stats["total_photos"], 0)
        self.assertEqual(stats["total_videos"], 0)
        self.assertEqual(stats["total_bytes"], 0)
        self.assertEqual(stats["total_albums"], 0)

    def test_save_and_check_media_item(self):
        """Test inserting media items and checking existence by ID."""
        item_id = "test_item_123"
        self.assertFalse(self.db.is_item_downloaded(item_id))

        self.db.save_media_item(
            item_id=item_id,
            filename="vacation.jpg",
            mime_type="image/jpeg",
            creation_time="2024-07-15T10:30:00Z",
            file_size=2048576,
            sha256="abc123hash456",
            local_path="/path/to/vacation.jpg",
            album_title="Summer 2024",
        )

        self.assertTrue(self.db.is_item_downloaded(item_id))
        self.assertFalse(self.db.is_item_downloaded("non_existent_id"))

    def test_deduplication_by_sha256(self):
        """Test duplicate detection using SHA-256 file hashes."""
        sha = "deadbeef12345678"
        self.assertIsNone(self.db.has_file_hash(sha))

        self.db.save_media_item(
            item_id="photo_1",
            filename="img1.jpg",
            mime_type="image/jpeg",
            creation_time="2024-01-01T00:00:00Z",
            file_size=1024,
            sha256=sha,
            local_path="/downloads/2024/01/img1.jpg",
        )

        existing_path = self.db.has_file_hash(sha)
        self.assertEqual(existing_path, "/downloads/2024/01/img1.jpg")

    def test_album_tracking(self):
        """Test saving and retrieving album metadata."""
        self.db.save_album("alb_1", "Family Trip", 42, "https://example.com/cover.jpg")
        albums = self.db.list_albums()
        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0]["title"], "Family Trip")
        self.assertEqual(albums[0]["total_media_items"], 42)

    def test_sync_runs_lifecycle(self):
        """Test tracking a sync run from start to finish."""
        run_id = self.db.start_sync_run()
        self.assertIsInstance(run_id, int)

        self.db.finish_sync_run(
            run_id=run_id,
            items_scanned=100,
            items_downloaded=85,
            bytes_downloaded=50000000,
            status="completed",
        )

        stats = self.db.get_stats()
        self.assertEqual(len(stats["recent_runs"]), 1)
        self.assertEqual(stats["recent_runs"][0]["status"], "completed")
        self.assertEqual(stats["recent_runs"][0]["items_downloaded"], 85)

if __name__ == "__main__":
    unittest.main()
