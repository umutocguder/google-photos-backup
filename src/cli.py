import argparse
import sys
from pathlib import Path
from src.config import config

def format_size(bytes_num: int) -> str:
    """Format bytes to human readable string (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

def cmd_auth(args):
    """Authenticate with Google Photos via OAuth 2.0."""
    try:
        from src.auth import GoogleAuthManager
    except ImportError as e:
        print(f"[-] Missing required dependencies: {e}")
        print("    Please install them using: pip install -r requirements.txt")
        return
    print("[*] Checking Google OAuth credentials...")
    auth = GoogleAuthManager()
    creds = auth.get_credentials()
    if creds and creds.valid:
        print("[+] Successfully authenticated! Token saved to token.json")
    else:
        print("[-] Authentication could not be completed.")

def cmd_status(args):
    """Display current backup and storage metrics."""
    from src.database import DatabaseManager
    db = DatabaseManager()
    stats = db.get_stats()

    print("\n" + "=" * 50)
    print("        GOOGLE PHOTOS BACKUP - STATUS")
    print("=" * 50)
    print(f" Total Media Files:  {stats['total_items']:,}")
    print(f" Photos:             {stats['total_photos']:,}")
    print(f" Videos:             {stats['total_videos']:,}")
    print(f" Total Storage:      {format_size(stats['total_bytes'])}")
    print(f" Tracked Albums:     {stats['total_albums']}")
    print(f" Backup Directory:   {config.downloads_dir}")
    print("=" * 50)

    recent = stats.get("recent_runs", [])
    if recent:
        print("\nRecent Sync Runs:")
        for r in recent:
            print(f"  [{r['started_at'][:19]}] Status: {r['status']} | Scanned: {r['items_scanned']} | Downloaded: {r['items_downloaded']} ({format_size(r['bytes_downloaded'] or 0)})")
    print()

def cmd_albums(args):
    """List Google Photos albums."""
    try:
        from src.client import GooglePhotosClient
        from src.database import DatabaseManager
    except ImportError as e:
        print(f"[-] Missing required dependencies: {e}")
        print("    Please install them using: pip install -r requirements.txt")
        return

    client = GooglePhotosClient()
    db = DatabaseManager()
    try:
        print("[*] Fetching albums from Google Photos...")
        albums = client.list_albums()
        print(f"\nFound {len(albums)} albums:")
        for alb in albums:
            title = alb.get("title", "Untitled")
            count = alb.get("mediaItemsCount", "0")
            print(f"  - {title} ({count} items) [ID: {alb['id']}]")
            db.save_album(alb["id"], title, int(count), alb.get("coverPhotoBaseUrl"))
    except Exception as e:
        print(f"[-] Error fetching albums: {e}")

def cmd_sync(args):
    """Run incremental backup sync."""
    try:
        from src.client import GooglePhotosClient
        from src.database import DatabaseManager
        from src.downloader import MediaDownloader
    except ImportError as e:
        print(f"[-] Missing required dependencies: {e}")
        print("    Please install them using: pip install -r requirements.txt")
        return

    client = GooglePhotosClient()
    db = DatabaseManager()
    downloader = MediaDownloader(
        db_manager=db,
        max_workers=args.workers or config.max_workers,
        organize_by=args.organize or config.organize_by,
    )

    run_id = db.start_sync_run()
    print(f"[*] Starting incremental sync run #{run_id}...")
    print(f"    Organizing by: {downloader.organize_by}")
    print(f"    Max workers:   {downloader.max_workers}")

    total_scanned = 0
    total_downloaded = 0
    total_deduplicated = 0
    total_bytes = 0

    try:
        batch = []
        for item in client.iterate_all_media_items(max_items=args.limit):
            batch.append(item)
            total_scanned += 1

            if len(batch) >= 25:
                res = downloader.download_batch_concurrent(batch)
                total_downloaded += res["downloaded"]
                total_deduplicated += res["deduplicated"]
                total_bytes += res["bytes"]
                print(f"  [Progress] Scanned: {total_scanned} | Downloaded: {total_downloaded} ({format_size(total_bytes)}) | Dedup: {total_deduplicated}")
                batch = []

        if batch:
            res = downloader.download_batch_concurrent(batch)
            total_downloaded += res["downloaded"]
            total_deduplicated += res["deduplicated"]
            total_bytes += res["bytes"]

        db.finish_sync_run(run_id, total_scanned, total_downloaded, total_bytes, "completed")
        print("\n[+] Sync completed successfully!")
        print(f"    Scanned:      {total_scanned}")
        print(f"    Downloaded:   {total_downloaded}")
        print(f"    Deduplicated: {total_deduplicated}")
        print(f"    Data:         {format_size(total_bytes)}")

    except Exception as e:
        db.finish_sync_run(run_id, total_scanned, total_downloaded, total_bytes, "failed", str(e))
        print(f"\n[-] Sync failed with error: {e}")

def cmd_takeout(args):
    """Import an unzipped Google Takeout archive."""
    source_dir = Path(args.path)
    if not source_dir.exists():
        print(f"[-] Directory not found: {source_dir}")
        return

    from src.takeout import TakeoutImporter
    print(f"[*] Scanning Google Takeout archive: {source_dir}...")
    importer = TakeoutImporter()
    res = importer.scan_and_import(source_dir, copy_files=not args.in_place)
    print("\n[+] Takeout import completed!")
    print(f"    Scanned:      {res['scanned']}")
    print(f"    Imported:     {res['imported']}")
    print(f"    Deduplicated: {res['deduplicated']}")
    print(f"    Errors:       {res['errors']}")

def cmd_web(args):
    """Launch local FastAPI web management dashboard."""
    try:
        import uvicorn
        from src.web.app import app
    except ImportError as e:
        print(f"[-] Missing web dependencies: {e}")
        print("    Please install them using: pip install -r requirements.txt")
        return
    host = args.host or config.web_host
    port = args.port or config.web_port
    print(f"[*] Launching Google Photos Backup Dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


def build_parser() -> argparse.ArgumentParser:
    """Build command-line interface argument parser."""
    parser = argparse.ArgumentParser(
        prog="gphotos-backup",
        description="High-performance, incremental Google Photos backup & sync tool.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # auth
    subparsers.add_parser("auth", help="Authorize with Google Photos via OAuth 2.0")

    # status
    subparsers.add_parser("status", help="Show backup metrics and storage usage")

    # albums
    subparsers.add_parser("albums", help="List all albums in Google Photos")

    # sync
    sync_p = subparsers.add_parser("sync", help="Run incremental backup download")
    sync_p.add_argument("--limit", type=int, default=None, help="Maximum items to process")
    sync_p.add_argument("--workers", type=int, default=5, help="Concurrent download threads")
    sync_p.add_argument("--organize", choices=["date", "album"], default="date", help="Directory layout")

    # takeout
    takeout_p = subparsers.add_parser("takeout", help="Import a Google Takeout folder")
    takeout_p.add_argument("path", help="Path to unzipped Takeout directory")
    takeout_p.add_argument("--in-place", action="store_true", help="Index files in-place without copying")

    # web
    web_p = subparsers.add_parser("web", help="Start local web dashboard")
    web_p.add_argument("--host", default="127.0.0.1", help="Bind host")
    web_p.add_argument("--port", type=int, default=8080, help="Bind port")

    return parser
