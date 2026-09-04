import tempfile
import unittest
from pathlib import Path
from src.database import DatabaseManager
from src.downloader import MediaDownloader

class TestMediaDownloader(unittest.TestCase):
    """Unit tests for downloader path resolution, sanitization, and naming logic."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.downloads_dir = Path(self.temp_dir.name)
        self.db_path = self.downloads_dir / "meta.db"
        self.db = DatabaseManager(db_path=self.db_path)
        self.downloader = MediaDownloader(
            db_manager=self.db,
            downloads_dir=self.downloads_dir,
            organize_by="date",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sanitize_filename(self):
        """Test cleaning illegal characters from filenames."""
        raw = "vacation/photo:2024*best?.jpg"
        clean = self.downloader._sanitize_filename(raw)
        self.assertNotIn("/", clean)
        self.assertNotIn(":", clean)
        self.assertNotIn("*", clean)
        self.assertNotIn("?", clean)
        self.assertTrue(clean.endswith(".jpg"))

    def test_determine_target_path_date_organization(self):
        """Test calculating target destination under date hierarchy (YYYY/MM)."""
        creation_time = "2023-08-15T14:22:00Z"
        path = self.downloader._determine_target_path(
            filename="beach.jpg",
            creation_time_str=creation_time,
        )
        self.assertTrue(path.is_relative_to(self.downloads_dir))
        self.assertIn("2023", path.parts)
        self.assertIn("08", path.parts)
        self.assertEqual(path.name, "beach.jpg")

    def test_determine_target_path_album_organization(self):
        """Test calculating target destination under album hierarchy."""
        downloader_album = MediaDownloader(
            db_manager=self.db,
            downloads_dir=self.downloads_dir,
            organize_by="album",
        )
        path = downloader_album._determine_target_path(
            filename="portrait.jpg",
            creation_time_str="2024-05-10T12:00:00Z",
            album_title="Family 2024",
        )
        self.assertIn("Albums", path.parts)
        self.assertIn("Family 2024", path.parts)
        self.assertEqual(path.name, "portrait.jpg")

    def test_filename_collision_avoidance(self):
        """Test that duplicate filenames are incremented with (1), (2)."""
        target1 = self.downloader._determine_target_path("doc.pdf", "2024-01-01T00:00:00Z")
        target1.touch()  # Simulate file already existing

        target2 = self.downloader._determine_target_path("doc.pdf", "2024-01-01T00:00:00Z")
        self.assertEqual(target2.name, "doc (1).pdf")

if __name__ == "__main__":
    unittest.main()
