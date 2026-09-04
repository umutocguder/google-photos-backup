# Project Worklog — Google Photos Backup

This document tracks all architectural decisions, implementations, and system handoffs for `google-photos-backup`.

---

### [2026-09-04 16:15] Initial Project Scaffolding & Architecture
- **Task & Objective**: Scaffold an incremental, deduplicating, high-performance Google Photos backup utility with dual-mode interfaces (Rich CLI and local FastAPI web dashboard), supporting full original resolution download, timestamp preservation, and Google Takeout reconciliation.
- **Technical Decisions & Architecture**:
  - **Modular Python Core**: Clean separation of concerns across `auth` (OAuth2), `client` (Google Photos API), `database` (SQLite3 deduplication & state), `downloader` (concurrent chunked fetch with EXIF/mtime sync), `takeout` (Takeout sidecar JSON parser), `cli` (Rich terminal), and `web` (FastAPI local dashboard).
  - **Deduplication Engine**: Media items are tracked with SHA-256 hashes, file sizes, and Google Photos IDs in `storage/metadata.db`.
  - **Organization Strategies**: Supports organizing by date (`YYYY/MM/`) or by Google Photos album names.
  - **Standard Compliance**: Initialized with standard 5 files (`AGENTS.md`, `CLAUDE.md`, `WORKLOG.md`, `README.md`, `.gitignore`).
- **Affected Files & Components**:
  - [AGENTS.md](file:///Users/umut/mycodespaces/google-photos-backup/AGENTS.md)
  - [CLAUDE.md](file:///Users/umut/mycodespaces/google-photos-backup/CLAUDE.md)
  - [WORKLOG.md](file:///Users/umut/mycodespaces/google-photos-backup/WORKLOG.md)
  - [README.md](file:///Users/umut/mycodespaces/google-photos-backup/README.md)
  - [.gitignore](file:///Users/umut/mycodespaces/google-photos-backup/.gitignore)
  - [requirements.txt](file:///Users/umut/mycodespaces/google-photos-backup/requirements.txt)
  - [pyproject.toml](file:///Users/umut/mycodespaces/google-photos-backup/pyproject.toml)
  - [main.py](file:///Users/umut/mycodespaces/google-photos-backup/main.py)
  - `src/` modules
- **Current Status & Verification**:
  - Project structure established.
  - Repository initialized on `main` branch.
- **Next Steps**:
  - Complete Python core implementation and verify syntax.
  - Create Private GitHub repository and push.
  - Register in Antigravity Projects config.

---

### [2026-09-05 00:20] Native iPhone Mirroring Keep-Alive Utility
- **Task & Objective**: Build a native macOS utility to prevent Mac and iPhone from sleeping during long backup sessions (e.g. iCloud Backup) by acquiring IOKit display sleep assertions and dispatching periodic subtle vertical swipe gestures directly to the active `iPhone Mirroring` (`com.apple.ScreenContinuity`) window.
- **Technical Decisions & Architecture**:
  - **Native Swift (`scripts/iphone_mirror_keepalive.swift`)**: Uses `IOKit.pwr_mgt` (`kIOPMAssertionTypePreventUserIdleDisplaySleep`) to block system/display sleep.
  - **Dynamic Window Lookup**: Uses `CGWindowListCopyWindowInfo` to detect the `iPhone Mirroring` window rect in real time.
  - **Seamless Mouse Cursor Preservation**: Automatically saves and restores the Mac pointer (`CGWarpMouseCursorPosition`) after each simulated gesture.
  - **Global Binary**: Compiled and installed to `~/.local/bin/iphone-keepalive`.
- **Affected Files & Components**:
  - [scripts/iphone_mirror_keepalive.swift](file:///Users/umut/mycodespaces/google-photos-backup/scripts/iphone_mirror_keepalive.swift)
  - [.gitignore](file:///Users/umut/mycodespaces/google-photos-backup/.gitignore)
  - [WORKLOG.md](file:///Users/umut/mycodespaces/google-photos-backup/WORKLOG.md)

