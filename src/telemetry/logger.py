# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

import os
import sys
import re
import json
import datetime
import urllib.request
import urllib.error
from .firebase_config import FIREBASE_ECOSYSTEM_CONFIG

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"pass(word)?", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"auth(orization)?", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"card[_-]?number", re.IGNORECASE),
    re.compile(r"credit[_-]?card", re.IGNORECASE),
    re.compile(r"cvv", re.IGNORECASE),
    re.compile(r"pin", re.IGNORECASE),
    re.compile(r"tckn", re.IGNORECASE)
]

TCKN_REGEX = re.compile(r"\b[1-9]\d{10}\b")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
BEARER_REGEX = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)

def scrub_sensitive_data(value):
    """Recursively scrub sensitive keys and patterns from log data."""
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = BEARER_REGEX.sub("Bearer ***REDACTED***", value)
        cleaned = CREDIT_CARD_REGEX.sub("***CARD_REDACTED***", cleaned)
        cleaned = TCKN_REGEX.sub("***TCKN_REDACTED***", cleaned)
        return cleaned

    if isinstance(value, list):
        return [scrub_sensitive_data(item) for item in value]

    if isinstance(value, dict):
        scrubbed = {}
        for k, v in value.items():
            key_str = str(k)
            if any(p.search(key_str) for p in SENSITIVE_KEY_PATTERNS):
                scrubbed[key_str] = "***REDACTED***"
            else:
                scrubbed[key_str] = scrub_sensitive_data(v)
        return scrubbed

    return value

def to_firestore_fields(obj):
    """Convert a Python dictionary into Cloud Firestore REST API typed value fields."""
    fields = {}
    if not isinstance(obj, dict):
        return fields

    for key, val in obj.items():
        if val is None:
            fields[key] = {"nullValue": None}
        elif isinstance(val, bool):
            fields[key] = {"booleanValue": val}
        elif isinstance(val, int):
            fields[key] = {"integerValue": str(val)}
        elif isinstance(val, float):
            fields[key] = {"doubleValue": val}
        elif isinstance(val, str):
            fields[key] = {"stringValue": val[:1000]}
        elif isinstance(val, (dict, list)):
            try:
                fields[key] = {"stringValue": json.dumps(val, ensure_ascii=False)[:1000]}
            except Exception:
                fields[key] = {"stringValue": "[Unserializable]"}
        else:
            fields[key] = {"stringValue": str(val)[:1000]}
    return fields

class TelemetryLogger:
    """
    Production-grade Telemetry & Cloud Firestore REST Streaming Logger.
    Complies with Rule 7, Rule 9, and Rule 18.
    """
    def __init__(self, app_name="google-photos-backup", app_version="1.0.0", log_dir=None):
        self.app_name = app_name
        self.app_version = app_version
        self.project_id = FIREBASE_ECOSYSTEM_CONFIG["project_id"]
        self.api_key = FIREBASE_ECOSYSTEM_CONFIG["api_key"]
        self.firestore_base_url = FIREBASE_ECOSYSTEM_CONFIG["firestore_base_url"]
        self.error_reporting_url = FIREBASE_ECOSYSTEM_CONFIG["error_reporting_url"]
        self.in_memory_buffer = []
        self.max_buffer = 100
        self.offline_queue = []
        self.max_offline_queue = 50

        # Local data custody
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

    def log(self, level, message, context=None, target_collection="app_logs"):
        """Record a structured log entry with automated PII scrubbing and cloud streaming."""
        try:
            scrubbed_context = scrub_sensitive_data(context or {})
            raw_msg = str(message) if message is not None else ""
            scrubbed_message = scrub_sensitive_data(raw_msg)

            entry = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "level": str(level).upper() if level else "INFO",
                "app_name": self.app_name,
                "app_version": self.app_version,
                "project_id": self.project_id,
                "target_collection": target_collection,
                "message": scrubbed_message,
                "context": scrubbed_context
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

            # 3. Cloud Firestore REST Dispatch (Non-blocking)
            self._dispatch_to_cloud(entry, target_collection)

            return entry
        except Exception:
            return None

    def debug(self, msg, ctx=None): return self.log("DEBUG", msg, ctx, "app_logs")
    def info(self, msg, ctx=None): return self.log("INFO", msg, ctx, "app_logs")
    def warn(self, msg, ctx=None): return self.log("WARN", msg, ctx, "app_logs")
    def error(self, msg, ctx=None): return self.log("ERROR", msg, ctx, "app_logs")
    def crash(self, msg, ctx=None): return self.log("CRASH", msg, ctx, "crash_logs")
    def security(self, event, ctx=None): return self.log("SECURITY", event, ctx, "security_audit_logs")
    def telemetry(self, event, ctx=None): return self.log("TELEMETRY", event, ctx, "telemetry_logs")
    def visitor(self, event, ctx=None): return self.log("VISITOR", event, ctx, "visitor_logs")
    def performance(self, metric, duration_ms, ctx=None):
        ctx_data = {"metric": metric, "duration_ms": duration_ms}
        if ctx:
            ctx_data.update(ctx)
        return self.log("PERF", f"Metric: {metric} - {duration_ms}ms", ctx_data, "telemetry_logs")

    def _dispatch_to_cloud(self, entry, collection="app_logs"):
        if not self.api_key:
            return

        firestore_url = f"{self.firestore_base_url}/{collection}?key={self.api_key}"
        payload = {
            "fields": to_firestore_fields({
                "event": f"{collection.upper()}_{entry['level']}",
                "timestamp": entry["timestamp"],
                "projectId": entry["project_id"],
                "appId": FIREBASE_ECOSYSTEM_CONFIG.get("app_id", ""),
                "appName": entry["app_name"],
                "appVersion": entry["app_version"],
                "logLevel": entry["level"],
                "message": entry["message"],
                "context": entry["context"]
            })
        }

        try:
            req = urllib.request.Request(
                firestore_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            self._enqueue_offline({"url": firestore_url, "payload": payload})

    def _enqueue_offline(self, item):
        try:
            self.offline_queue.append(item)
            if len(self.offline_queue) > self.max_offline_queue:
                self.offline_queue.pop(0)
        except Exception:
            pass

    def flush_offline_queue(self):
        if not self.offline_queue:
            return
        items = list(self.offline_queue)
        self.offline_queue = []
        for item in items:
            try:
                req = urllib.request.Request(
                    item["url"],
                    data=json.dumps(item["payload"]).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=1.5):
                    pass
            except Exception:
                self._enqueue_offline(item)

    def get_recent_logs(self, limit=50):
        return self.in_memory_buffer[-limit:]

    def export_logs_as_json(self):
        return json.dumps(self.in_memory_buffer, indent=2, ensure_ascii=False)

    def clear_logs(self):
        self.in_memory_buffer = []
        self.offline_queue = []
        if self.log_file and os.path.exists(self.log_file):
            try:
                os.remove(self.log_file)
            except Exception:
                pass

logger = TelemetryLogger()
