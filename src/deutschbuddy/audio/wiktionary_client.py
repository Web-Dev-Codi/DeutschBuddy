"""Client for fetching German pronunciation audio from Wiktionary."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote

if TYPE_CHECKING:
    pass


class WiktionaryClient:
    """Fetches German pronunciation audio files from Wiktionary.

    Scrapes the German Wiktionary page for a word and extracts the
    pronunciation audio file URL (typically .ogg format hosted on Wikimedia Commons).
    """

    BASE_URL = "https://de.wiktionary.org/wiki/{word}"
    COMMONS_BASE = "https://commons.wikimedia.org/wiki/File:{filename}"
    COMMONS_DOWNLOAD = "https://upload.wikimedia.org/wikipedia/commons/{hash_prefix}/{filename}"

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the Wiktionary client.

        Args:
            cache_dir: Directory to cache downloaded audio files
        """
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            import requests
            self._requests = requests
            self._has_requests = True
        except ImportError:
            self._has_requests = False
            self._requests = None

    def fetch_audio(self, word: str) -> Path | None:
        """Fetch pronunciation audio for a German word.

        Args:
            word: German word to look up

        Returns:
            Path to the cached audio file, or None if not found
        """
        if not word or not word.strip():
            return None

        word = word.strip().lower()

        if self.cache_dir:
            cached = self._get_cached_path(word)
            if cached.exists():
                return cached

        audio_url = self._find_audio_url(word)
        if not audio_url:
            return None

        if self.cache_dir:
            return self._download_and_cache(word, audio_url)
        return None

    def _find_audio_url(self, word: str) -> str | None:
        """Scrape Wiktionary page to find the pronunciation audio URL.

        Args:
            word: German word to look up

        Returns:
            Direct URL to the audio file, or None if not found
        """
        if not self._has_requests:
            return None

        try:
            url = self.BASE_URL.format(word=quote(word))
            response = self._requests.get(url, timeout=10)
            response.raise_for_status()
            html = response.text

            return self._extract_audio_url(html, word)
        except Exception:
            return None

    def _extract_audio_url(self, html: str, word: str) -> str | None:
        """Extract audio file URL from Wiktionary HTML.

        Looks for:
        1. Audio player elements with .ogg links
        2. Wikimedia Commons file references

        Args:
            html: Wiktionary page HTML
            word: Original word (for logging/debugging)

        Returns:
            Direct URL to audio file, or None
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        audio_links = soup.find_all("a", href=re.compile(r"\.ogg$"))

        for link in audio_links:
            href = link.get("href", "")
            if "De-" in href or "de-" in href.lower():
                if href.startswith("//"):
                    return "https:" + href
                elif href.startswith("/"):
                    return "https://de.wiktionary.org" + href
                elif href.startswith("http"):
                    return href

        commons_pattern = re.compile(r'commons\.wikimedia\.org/wiki/File:([^"\'\s]+\.ogg)')
        match = commons_pattern.search(html)
        if match:
            filename = unquote(match.group(1))
            return self._commons_to_direct_url(filename)

        upload_pattern = re.compile(r'upload\.wikimedia\.org/wikipedia/commons/[^"\'\s]+\.ogg')
        match = upload_pattern.search(html)
        if match:
            return "https://" + match.group(0)

        return None

    def _commons_to_direct_url(self, filename: str) -> str:
        """Convert Wikimedia Commons filename to direct download URL.

        Args:
            filename: Commons filename (e.g., "De-hallo.ogg")

        Returns:
            Direct URL to the file on upload.wikimedia.org
        """
        filename_encoded = filename.replace(" ", "_")

        hash_prefix = self._compute_hash_prefix(filename_encoded)

        return self.COMMONS_DOWNLOAD.format(
            hash_prefix=hash_prefix,
            filename=filename_encoded,
        )

    def _compute_hash_prefix(self, filename: str) -> str:
        """Compute the MD5 hash prefix for Wikimedia Commons URL.

        Args:
            filename: Encoded filename

        Returns:
            Hash prefix like '0/0a' from the first characters of MD5
        """
        import hashlib

        md5 = hashlib.md5(filename.encode("utf-8")).hexdigest()
        return f"{md5[0]}/{md5[:2]}"

    def _get_cached_path(self, word: str) -> Path:
        """Get the cache file path for a word.

        Args:
            word: German word

        Returns:
            Path to cached audio file
        """
        safe_word = re.sub(r"[^\w\-]", "_", word.lower())
        return self.cache_dir / f"{safe_word}.ogg"

    def _download_and_cache(self, word: str, audio_url: str) -> Path | None:
        """Download audio file and cache it locally.

        Args:
            word: German word
            audio_url: URL to download from

        Returns:
            Path to cached file, or None on failure
        """
        cache_path = self._get_cached_path(word)

        try:
            if self._has_requests:
                response = self._requests.get(audio_url, timeout=15, stream=True)
                response.raise_for_status()
                with open(cache_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                urllib.request.urlretrieve(audio_url, cache_path)

            return cache_path if cache_path.exists() else None
        except Exception:
            if cache_path.exists():
                cache_path.unlink()
            return None
