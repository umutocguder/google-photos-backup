# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

import os

FIREBASE_ECOSYSTEM_CONFIG = {
    "project_id": "hopem-software-cloud",
    "project_number": "691994382715",
    "app_id": "1:691994382715:web:11hopem-google-photos-backup",
    "api_key": os.getenv("FIREBASE_API_KEY", "AIzaSyA4Q68qVv5Z3s-HopemDefaultKey"),
    "account": "umutocgdr@gmail.com",
    "firestore_base_url": "https://firestore.googleapis.com/v1/projects/hopem-software-cloud/databases/(default)/documents",
    "cloud_logging_url": "https://logging.googleapis.com/v2/entries:write",
    "error_reporting_url": "https://clouderrorreporting.googleapis.com/v1beta1/projects/hopem-software-cloud/events:report"
}
