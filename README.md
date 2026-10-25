<!-- Created by 11Hopem -->
# 📸 Google Photos Backup & Takeout Reconciliation Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?logo=python)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/UI-FastAPI%20Web%20Dashboard-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Storage](https://img.shields.io/badge/indexing-SQLite3%20%7C%20SHA--256-blue.svg)](#features)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://11hopem.com)
[![Created by 11Hopem](https://img.shields.io/badge/created%20by-11Hopem-orange.svg)](https://11hopem.com)

A high-performance, incremental, and deduplicating backup engine for Google Photos. Features full original resolution downloads, automated EXIF timestamp preservation, SHA-256 deduplication, Google Takeout metadata reconciliation, and a dual-mode interface (Rich terminal CLI + local FastAPI Web Dashboard).

---

## 🌟 Key Features

- **Full Resolution Preservation**: Downloads photos and videos at original uploaded resolution (`=d` and `=dv` download directives).
- **Incremental & Resumable Sync**: Maintains an indexed local SQLite catalog (`storage/metadata.db`). Automatically skips already archived media and resumes interrupted downloads.
- **SHA-256 Deduplication**: Prevents duplicate file storage even if identical photos appear in multiple albums or takeout folders.
- **EXIF & Timestamp Fidelity**: Restores accurate photo capture timestamps directly onto filesystem creation and modification metadata (`mtime`/`atime`).
- **Google Takeout Importer**: Ingests massive Google Takeout archives, parses companion JSON metadata sidecars, and merges them into the unified local library.
- **Dual-Mode Control**:
  - **Terminal CLI**: Fast, headless automation suitable for cron / background schedules.
  - **Local Web UI**: Modern FastAPI dashboard with real-time download graphs, album browsing, and disk usage metrics.

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────┐
│       Google Photos Library API / Takeout     │
└───────────────────────┬───────────────────────┘
                        │ OAuth 2.0 / Read-Only
                        ▼
┌───────────────────────────────────────────────┐
│            Sync & Download Worker             │
│   • Original Quality Streams                  │
│   • EXIF Date Injection                       │
│   • SHA-256 Hash Calculation                  │
└───────────────────────┬───────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐          ┌─────────────────┐
│ SQLite Metadata  │          │ Local Disk Arch │
│  Indexed State   │          │  YYYY/MM/ Files │
└──────────────────┘          └─────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Google Cloud Project with the **Google Photos Library API** enabled (OAuth 2.0 Client ID)

### 1. Clone & Install

```bash
git clone https://github.com/umutocguder/google-photos-backup.git
cd google-photos-backup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup Google Credentials

Place your downloaded OAuth `credentials.json` into the root directory:

```bash
cp /path/to/downloaded/credentials.json ./credentials.json
```

### 3. Run Command Line Sync

```bash
# Preview upcoming media downloads
python3 main.py --dry-run

# Run full incremental sync
python3 main.py
```

### 4. Run Local Web Dashboard

```bash
python3 -m uvicorn src.web:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🧪 Testing

```bash
python3 -m unittest discover -s tests
```

---

## 🛡️ License & Attribution

Created by [11Hopem](https://11hopem.com).  
Copyright © 2026 11Hopem. All rights reserved.  
Licensed under the [MIT License](LICENSE).  
Official website: [https://11hopem.com](https://11hopem.com)
