"""Client for fetching German pronunciation audio from Wiktionary."""

from __future__ import annotations

import logging
import re
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import unquote

try:
    import mwclient
except ImportError:
    mwclient = None


LOGGER = logging.getLogger(__name__)


class WiktionaryClient:
    """Fetches German pronunciation audio files from Wiktionary."""

    AUDIO_EXTENSIONS = (".ogg", ".oga", ".mp3", ".wav")
    GERMAN_AUDIO_PATTERN = re.compile(r"^de(?:-[a-z0-9]+)*-", re.IGNORECASE)
    NORMALIZE_PATTERN = re.compile(r"[^0-9a-zäöüß]+", re.IGNORECASE)
    USER_AGENT = "DeutschBuddy/0.6.5 (local terminal app)"

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the Wiktionary client.

        Args:
            cache_dir: Directory to cache downloaded audio files
        """
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
        self._wiktionary_site = None
        self._commons_site = None

    def is_available(self) -> bool:
        return mwclient is not None

    def fetch_audio(self, word: str) -> Path | None:
        """Fetch pronunciation audio for a German word.

        Args:
            word: German word to look up

        Returns:
            Path to the cached audio file, or None if not found
        """
        if not word or not word.strip():
            return None

        lookup_word = word.strip()

        if self.cache_dir:
            cached = self._get_cached_path(lookup_word)
            if cached is not None:
                return cached

        audio_title = self._find_audio_title(lookup_word)
        if not audio_title or not self.cache_dir:
            return None

        return self._download_and_cache(lookup_word, audio_title)

    def _find_audio_title(self, word: str) -> str | None:
        """Resolve the best matching Wiktionary audio file title for a word.

        Args:
            word: German word to look up

        Returns:
            Canonical Commons file title, or None if not found
        """
        site = self._get_wiktionary_site()
        if site is None:
            return None

        image_titles = self._fetch_image_titles_from_parse(site, word)
        if not image_titles:
            image_titles = self._fetch_image_titles_from_query(site, word)

        return self._select_best_audio_title(image_titles, word)

    def _fetch_image_titles_from_parse(self, site, word: str) -> list[str]:
        try:
            response = site.api("parse", "GET", page=word, redirects=1, prop="images")
        except Exception as exc:
            LOGGER.debug("Wiktionary parse lookup failed for '%s': %s", word, exc)
            return []

        return [
            self._canonicalize_file_title(title)
            for title in response.get("parse", {}).get("images", [])
            if title
        ]

    def _fetch_image_titles_from_query(self, site, word: str) -> list[str]:
        try:
            response = site.api(
                "query",
                "GET",
                titles=word,
                redirects=1,
                prop="images|links",
                imlimit="max",
                plnamespace="6",
                pllimit="max",
            )
        except Exception as exc:
            LOGGER.warning("Wiktionary media lookup failed for '%s': %s", word, exc)
            return []

        image_titles: list[str] = []
        for page in response.get("query", {}).get("pages", {}).values():
            for image in page.get("images", []):
                title = image.get("title")
                if title:
                    image_titles.append(self._canonicalize_file_title(title))
            for link in page.get("links", []):
                title = link.get("title")
                if title:
                    image_titles.append(self._canonicalize_file_title(title))
        return list(dict.fromkeys(image_titles))

    def _select_best_audio_title(self, image_titles: list[str], word: str) -> str | None:
        target = self._normalize_for_match(word)
        ranked_titles: list[tuple[tuple[int, int, int, int, int], str]] = []

        for title in image_titles:
            filename = self._strip_file_namespace(title)
            if not self._is_audio_filename(filename):
                continue

            score = self._score_audio_filename(filename, target)
            if score is None:
                continue

            ranked_titles.append((score, title))

        if not ranked_titles:
            return None

        ranked_titles.sort(key=lambda item: item[0], reverse=True)
        return ranked_titles[0][1]

    def _score_audio_filename(self, filename: str, target: str) -> tuple[int, int, int, int, int] | None:
        stem = Path(filename).stem
        normalized_full = self._normalize_for_match(stem)
        normalized_without_prefix = self._normalize_for_match(
            self.GERMAN_AUDIO_PATTERN.sub("", stem)
        )

        if normalized_without_prefix == target:
            match_rank = 3
        elif normalized_full == target:
            match_rank = 2
        elif target and (target in normalized_without_prefix or target in normalized_full):
            match_rank = 1
        else:
            return None

        comparison_value = normalized_without_prefix or normalized_full
        distance = abs(len(comparison_value) - len(target))
        prefix_rank = self._prefix_rank(stem)
        extension_rank = self._extension_rank(filename)

        return (
            match_rank,
            prefix_rank,
            extension_rank,
            -distance,
            -len(comparison_value),
        )

    def _resolve_audio_url(self, file_title: str) -> str | None:
        site = self._get_commons_site()
        if site is None:
            return None

        try:
            response = site.api(
                "query",
                "GET",
                titles=self._canonicalize_file_title(file_title),
                redirects=1,
                prop="imageinfo",
                iiprop="url|mime",
            )
        except Exception as exc:
            LOGGER.warning("Commons file lookup failed for '%s': %s", file_title, exc)
            return None

        for page in response.get("query", {}).get("pages", {}).values():
            imageinfo = page.get("imageinfo") or []
            if imageinfo:
                url = imageinfo[0].get("url")
                if url:
                    return url

        return None

    def _get_cached_path(self, word: str) -> Path | None:
        if not self.cache_dir:
            return None

        safe_word = re.sub(r"[^\w\-]", "_", word.lower())
        for extension in self.AUDIO_EXTENSIONS:
            cache_path = self.cache_dir / f"{safe_word}{extension}"
            if cache_path.exists():
                return cache_path

        return None

    def _build_cache_path(self, word: str, file_title: str) -> Path:
        suffix = Path(self._strip_file_namespace(file_title)).suffix.lower() or ".ogg"
        safe_word = re.sub(r"[^\w\-]", "_", word.lower())
        return self.cache_dir / f"{safe_word}{suffix}"

    def _download_and_cache(self, word: str, file_title: str) -> Path | None:
        audio_url = self._resolve_audio_url(file_title)
        if not audio_url:
            return None

        cache_path = self._build_cache_path(word, file_title)

        try:
            request = urllib.request.Request(audio_url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(request, timeout=20) as response, cache_path.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            return cache_path if cache_path.exists() else None
        except Exception as exc:
            LOGGER.warning("Failed to download Wiktionary audio for '%s': %s", word, exc)
            if cache_path.exists():
                cache_path.unlink()
            return None

    def _get_wiktionary_site(self):
        if self._wiktionary_site is None:
            self._wiktionary_site = self._build_site("de.wiktionary.org")
        return self._wiktionary_site

    def _get_commons_site(self):
        if self._commons_site is None:
            self._commons_site = self._build_site("commons.wikimedia.org")
        return self._commons_site

    def _build_site(self, host: str):
        if mwclient is None:
            LOGGER.warning("mwclient is not installed; Wiktionary audio lookup is disabled")
            return None

        try:
            return mwclient.Site(
                host,
                scheme="https",
                force_login=False,
                clients_useragent=self.USER_AGENT,
                connection_options={"timeout": 15},
                max_retries=2,
                retry_timeout=5,
            )
        except Exception as exc:
            LOGGER.warning("Failed to initialize MediaWiki client for '%s': %s", host, exc)
            return None

    def _canonicalize_file_title(self, title: str) -> str:
        readable_title = unquote(title).replace("_", " ").strip()
        if ":" in readable_title:
            _, filename = readable_title.split(":", 1)
            return f"File:{filename}"
        return f"File:{readable_title}"

    def _strip_file_namespace(self, title: str) -> str:
        if ":" in title:
            return title.split(":", 1)[1]
        return title

    def _is_audio_filename(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in self.AUDIO_EXTENSIONS

    def _prefix_rank(self, stem: str) -> int:
        lower_stem = stem.lower()
        if lower_stem.startswith("de-") and not re.match(r"^de-[a-z]{2,3}-", lower_stem):
            return 2
        if self.GERMAN_AUDIO_PATTERN.match(stem):
            return 1
        return 0

    def _extension_rank(self, filename: str) -> int:
        extension = Path(filename).suffix.lower()
        return {
            ".ogg": 3,
            ".oga": 2,
            ".mp3": 1,
            ".wav": 0,
        }.get(extension, 0)

    def _normalize_for_match(self, value: str) -> str:
        return self.NORMALIZE_PATTERN.sub("", value.casefold())
