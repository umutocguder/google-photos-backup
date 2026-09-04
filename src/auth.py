import json
import os
from pathlib import Path
from typing import Optional
from src.config import config

# Required read-only scope for Google Photos Library
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]

class GoogleAuthManager:
    """Handles OAuth 2.0 user authorization, token storage, and refresh lifecycle."""

    def __init__(
        self,
        credentials_path: Optional[Path] = None,
        token_path: Optional[Path] = None,
    ):
        self.credentials_path = credentials_path or config.credentials_path
        self.token_path = token_path or config.token_path

    def get_credentials(self):
        """
        Retrieve valid Google OAuth credentials.
        Refreshes expired tokens or launches authorization flow if needed.
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise ImportError(
                "Missing Google Auth dependencies. Install them via: pip install google-auth-oauthlib google-auth"
            )

        creds = None

        # 1. Check if token.json already exists
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                print(f"[Warning] Failed to load cached token: {e}")
                creds = None

        # 2. Refresh or initiate new flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[Info] Token refresh failed ({e}), requesting new authorization.")
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    self._show_credentials_setup_guide()
                    return None

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                try:
                    # Attempt loopback local server flow
                    creds = flow.run_local_server(port=0)
                except Exception:
                    # Fallback to console code authorization
                    creds = flow.run_console()

            # Save the valid token for future runs
            if creds:
                with open(self.token_path, "w") as token_file:
                    token_file.write(creds.to_json())

        return creds

    def is_authenticated(self) -> bool:
        """Check whether valid token credentials currently exist."""
        if not self.token_path.exists():
            return False
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            return bool(creds and (creds.valid or creds.refresh_token))
        except Exception:
            return False

    def _show_credentials_setup_guide(self) -> None:
        """Display clear setup instructions when credentials.json is missing."""
        guide = f"""
================================================================================
               GOOGLE PHOTOS OAUTH CREDENTIALS REQUIRED
================================================================================
To backup your Google Photos, you need a free Google Cloud OAuth Client ID:

1. Visit the Google Cloud Console:
   https://console.cloud.google.com/apis/credentials

2. Create a new project (e.g. 'Photos Backup') or select an existing one.

3. Enable the 'Photos Library API':
   https://console.cloud.google.com/apis/library/photoslibrary.googleapis.com

4. Configure your OAuth Consent Screen:
   - User Type: External
   - Add your own email as a Test User

5. Create Credentials:
   - Click 'Create Credentials' -> 'OAuth client ID'
   - Application Type: 'Desktop App'
   - Name: 'Google Photos Backup CLI'

6. Download the JSON file, rename it to 'credentials.json', and place it in:
   {self.credentials_path}
================================================================================
"""
        print(guide)
