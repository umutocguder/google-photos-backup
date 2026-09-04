#!/usr/bin/env python3
"""
Google Photos Backup - Entrypoint script.
Provides CLI management and local web dashboard launcher.
"""

import sys
from src.cli import (
    build_parser,
    cmd_auth,
    cmd_sync,
    cmd_status,
    cmd_albums,
    cmd_takeout,
    cmd_web,
)

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch_table = {
        "auth": cmd_auth,
        "sync": cmd_sync,
        "status": cmd_status,
        "albums": cmd_albums,
        "takeout": cmd_takeout,
        "web": cmd_web,
    }

    handler = dispatch_table.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
