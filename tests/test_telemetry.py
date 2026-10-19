# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

import unittest
import tempfile
import os
import json
from src.telemetry.firebase_config import FIREBASE_ECOSYSTEM_CONFIG
from src.telemetry.logger import TelemetryLogger, scrub_sensitive_data, to_firestore_fields

class TestTelemetryLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.logger = TelemetryLogger(
            app_name="photos-test",
            app_version="1.0.0",
            log_dir=self.temp_dir.name
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_firebase_config(self):
        self.assertEqual(FIREBASE_ECOSYSTEM_CONFIG["account"], "umutocgdr@gmail.com")
        self.assertEqual(FIREBASE_ECOSYSTEM_CONFIG["project_id"], "hopem-software-cloud")
        self.assertTrue("hopem-software-cloud" in FIREBASE_ECOSYSTEM_CONFIG["firestore_base_url"])

    def test_log_writing_and_local_custody(self):
        entry = self.logger.info("Backup scan started", {"files_found": 42})
        self.assertEqual(entry["level"], "INFO")
        self.assertEqual(entry["app_name"], "photos-test")
        self.assertEqual(entry["context"]["files_found"], 42)
        self.assertEqual(entry["target_collection"], "app_logs")

        error_entry = self.logger.error("Network timeout", {"retry": 1})
        self.assertEqual(error_entry["level"], "ERROR")

        # Verify JSONL file exists and is populated
        self.assertTrue(os.path.exists(self.logger.log_file))
        with open(self.logger.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            parsed = json.loads(lines[0])
            self.assertEqual(parsed["message"], "Backup scan started")

    def test_scrub_sensitive_data(self):
        dirty = {
            "password": "SecretPassword123",
            "api_key": "AIzaSySecretKey",
            "token": "Bearer super-oauth-token",
            "user": {
                "tckn": "12345678901",
                "credit_card": "4543 1234 5678 9012"
            },
            "msg": "Client with TCKN 12345678901 used card 4543 1234 5678 9012 and Bearer tok-456"
        }
        clean = scrub_sensitive_data(dirty)
        self.assertEqual(clean["password"], "***REDACTED***")
        self.assertEqual(clean["api_key"], "***REDACTED***")
        self.assertEqual(clean["token"], "***REDACTED***")
        self.assertEqual(clean["user"]["tckn"], "***REDACTED***")
        self.assertEqual(clean["user"]["credit_card"], "***REDACTED***")
        self.assertNotIn("12345678901", clean["msg"])
        self.assertNotIn("4543 1234 5678 9012", clean["msg"])
        self.assertNotIn("tok-456", clean["msg"])

    def test_to_firestore_fields(self):
        fields = to_firestore_fields({
            "appName": "google-photos-backup",
            "photosCount": 1500,
            "progress": 75.5,
            "done": False,
            "error": None,
            "tags": ["family", "vacation"]
        })
        self.assertEqual(fields["appName"], {"stringValue": "google-photos-backup"})
        self.assertEqual(fields["photosCount"], {"integerValue": "1500"})
        self.assertEqual(fields["progress"], {"doubleValue": 75.5})
        self.assertEqual(fields["done"], {"booleanValue": False})
        self.assertEqual(fields["error"], {"nullValue": None})
        self.assertIn("family", fields["tags"]["stringValue"])

    def test_multi_collection_routing(self):
        sec = self.logger.security("OAuth token revoked", {"user": "test-user"})
        self.assertEqual(sec["target_collection"], "security_audit_logs")

        tel = self.logger.telemetry("Chunk download time", {"chunk_size_mb": 50})
        self.assertEqual(tel["target_collection"], "telemetry_logs")

        vis = self.logger.visitor("Takeout download archive downloaded", {"archive_id": 1})
        self.assertEqual(vis["target_collection"], "visitor_logs")

        cr = self.logger.crash("Worker thread segment failure", {"thread": 3})
        self.assertEqual(cr["target_collection"], "crash_logs")

        perf = self.logger.performance("hashing_file", 85)
        self.assertEqual(perf["target_collection"], "telemetry_logs")

    def test_zero_crash_guarantee(self):
        res1 = self.logger.log(None, None)
        self.assertIsNotNone(res1)
        res2 = self.logger.error(Exception("Test failure"))
        self.assertIsNotNone(res2)

if __name__ == "__main__":
    unittest.main()
