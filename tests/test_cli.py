import unittest
from src.cli import build_parser, format_size

class TestCLI(unittest.TestCase):
    """Unit tests for CLI parser and format utilities."""

    def test_format_size_bytes(self):
        """Test human readable byte format conversion."""
        self.assertEqual(format_size(500), "500.0 B")
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1048576), "1.0 MB")
        self.assertEqual(format_size(1073741824), "1.0 GB")

    def test_parser_subcommands(self):
        """Test argument parsing for all supported subcommands."""
        parser = build_parser()

        # auth
        args_auth = parser.parse_args(["auth"])
        self.assertEqual(args_auth.command, "auth")

        # status
        args_status = parser.parse_args(["status"])
        self.assertEqual(args_status.command, "status")

        # albums
        args_albums = parser.parse_args(["albums"])
        self.assertEqual(args_albums.command, "albums")

        # sync with flags
        args_sync = parser.parse_args(["sync", "--limit", "50", "--workers", "8", "--organize", "album"])
        self.assertEqual(args_sync.command, "sync")
        self.assertEqual(args_sync.limit, 50)
        self.assertEqual(args_sync.workers, 8)
        self.assertEqual(args_sync.organize, "album")

        # takeout
        args_takeout = parser.parse_args(["takeout", "/dummy/path", "--in-place"])
        self.assertEqual(args_takeout.command, "takeout")
        self.assertEqual(args_takeout.path, "/dummy/path")
        self.assertTrue(args_takeout.in_place)

        # web
        args_web = parser.parse_args(["web", "--port", "9000"])
        self.assertEqual(args_web.command, "web")
        self.assertEqual(args_web.port, 9000)

if __name__ == "__main__":
    unittest.main()
