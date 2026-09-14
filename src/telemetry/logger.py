# Created by 11hopem (11 Hopem Software Ltd. Şti.)
# Copyright (c) 2026 11hopem. All rights reserved.
# Licensed under 11 Hopem Software Proprietary License.

import json
import os
import sys
import datetime
import urllib.request
import urllib.error
from .firebase_config import FIREBASE_ECOSYSTEM_CONFIG

class TelemetryLogger:
    """
    In-Project Telemetry and Cloud Logging Client for Python applications.
    Conforms to AGENTS.md Rule 7 (Firebase & Local Data Custody Standard).
    """
    def __init__(self, app_name="google-photos-backup", app_version="1.0.0", log_dir=None):
        self.app_name = app_name
        self.app_version = app_version
        self.project_id = FIREBASE_ECOSYSTEM_CONFIG["project_id"]
        self.error_reporting_url = FIREBASE_ECOSYSTEM_CONFIG["error_reporting_url"]
        self.in_memory_buffer = []
        self.max_buffer = 100
        
        # Local custody log file
        if log_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.log_dir = os.path.join(base_dir, "storage", "logs")
        else:
            self.log_dir = log_dir
            
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            self.log_file = os.path.join(self.log_dir, f"{self.app_name}_telemetry.jsonl")
        except Exception:
            self.log_file = None

    def log(self, level, message, context=None):
        try:
            entry = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "level": str(level).upper(),
                "app_name": self.app_name,
                "app_version": self.app_version,
                "project_id": self.project_id,
                "message": str(message),
                "context": context or {}
            }

            # 1. In-memory buffer
            self.in_memory_buffer.append(entry)
            if len(self.in_memory_buffer) > self.max_buffer:
                self.in_memory_buffer.pop(0)

            # 2. Local Data Custody (JSONL)
            if self.log_file:
                try:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                except Exception:
                    pass

            # 3. Cloud / Firebase Dispatch (Non-blocking)
            if entry["level"] in ("ERROR", "CRASH"):
                self._dispatch_to_cloud(entry)

            return entry
        except Exception:
            return None

    def info(self, msg, ctx=None): return self.log("INFO", msg, ctx)
    def warn(self, msg, ctx=None): return self.log("WARN", msg, ctx)
    def error(self, msg, ctx=None): return self.log("ERROR", msg, ctx)
    def crash(self, msg, ctx=None): return self.log("CRASH", msg, ctx)

    def _dispatch_to_cloud(self, entry):
        try:
            payload = {
                "eventTime": entry["timestamp"],
                "serviceContext": {"service": entry["app_name"], "version": entry["app_version"]},
                "message": f"[{entry['level']}] {entry['message']}\nContext: {json.dumps(entry['context'])}"
            }
            req = urllib.request.Request(
                self.error_reporting_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            # Short timeout to ensure zero-crash and non-blocking operation
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            # Zero-Crash guarantee
            pass

    def get_recent_logs(self, limit=50):
        return self.in_memory_buffer[-limit:]

    def export_logs_as_json(self):
        return json.dumps(self.in_memory_buffer, indent=2, ensure_ascii=False)

logger = TelemetryLogger()
