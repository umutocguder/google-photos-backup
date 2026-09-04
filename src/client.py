import time
from typing import Any, Dict, Generator, List, Optional
import requests
from src.auth import GoogleAuthManager

API_BASE_URL = "https://photoslibrary.googleapis.com/v1"

class GooglePhotosClient:
    """Client for the Google Photos Library API v1."""

    def __init__(self, auth_manager: Optional[GoogleAuthManager] = None):
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.creds = None

    def _ensure_authenticated(self) -> Dict[str, str]:
        """Ensure valid credentials and return HTTP authorization headers."""
        if not self.creds or not self.creds.valid:
            self.creds = self.auth_manager.get_credentials()
            if not self.creds:
                raise RuntimeError("Authentication failed. Please verify credentials.json.")
        
        return {
            "Authorization": f"Bearer {self.creds.token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Execute HTTP request with exponential backoff on rate limits."""
        url = f"{API_BASE_URL}/{endpoint}"
        max_retries = 3
        backoff = 2.0

        for attempt in range(max_retries):
            headers = self._ensure_authenticated()
            try:
                response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                elif response.status_code == 401:
                    # Token might have expired during long sync, force refresh
                    self.creds = None
                    continue
                else:
                    response.raise_for_status()
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(backoff)
                backoff *= 2

        return {}

    def list_media_items(self, page_size: int = 100, page_token: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a page of media items from the user's library."""
        params = {"pageSize": min(page_size, 100)}
        if page_token:
            params["pageToken"] = page_token
        return self._make_request("GET", "mediaItems", params=params)

    def iterate_all_media_items(self, max_items: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """Generator yielding media items across multiple paginated API calls."""
        next_token = None
        count = 0

        while True:
            data = self.list_media_items(page_size=100, page_token=next_token)
            items = data.get("mediaItems", [])
            for item in items:
                yield item
                count += 1
                if max_items and count >= max_items:
                    return

            next_token = data.get("nextPageToken")
            if not next_token:
                break

    def list_albums(self, page_size: int = 50) -> List[Dict[str, Any]]:
        """Retrieve all user-created albums."""
        albums = []
        next_token = None

        while True:
            params = {"pageSize": page_size}
            if next_token:
                params["pageToken"] = next_token

            data = self._make_request("GET", "albums", params=params)
            albums.extend(data.get("albums", []))
            next_token = data.get("nextPageToken")
            if not next_token:
                break

        return albums

    def list_album_media_items(self, album_id: str) -> Generator[Dict[str, Any], None, None]:
        """Retrieve all media items belonging to a specific album."""
        next_token = None
        while True:
            payload: Dict[str, Any] = {"albumId": album_id, "pageSize": 100}
            if next_token:
                payload["pageToken"] = next_token

            data = self._make_request("POST", "mediaItems:search", json=payload)
            items = data.get("mediaItems", [])
            for item in items:
                yield item

            next_token = data.get("nextPageToken")
            if not next_token:
                break
