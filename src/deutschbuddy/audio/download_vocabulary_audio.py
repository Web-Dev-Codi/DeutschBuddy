from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import yaml


WIKTIONARY_API_URL = "https://en.wiktionary.org/w/api.php"
COMMONS_UPLOAD_BASE_URL = "https://upload.wikimedia.org/wikipedia/commons"
REQUEST_DELAY_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = "DeutschBuddy/0.6.5 vocabulary audio downloader"
UMLAUT_FILENAME_TRANSLATION = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
)
MATCH_TRANSLATION = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
)
GERMAN_AUDIO_PREFIX_PATTERN = re.compile(r"^de(?:-[a-z0-9]+)*-", re.IGNORECASE)
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^0-9a-z]+", re.IGNORECASE)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_words(words_path: Path) -> list[str]:
    # Load and validate the YAML vocabulary file.
    if not words_path.exists():
        raise FileNotFoundError(f"YAML file not found: {words_path}")

    with words_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError("words.yaml must contain a top-level mapping with a 'words' key")

    raw_words = data.get("words")
    if not isinstance(raw_words, list):
        raise ValueError("words.yaml must contain a 'words' list")

    words: list[str] = []
    for item in raw_words:
        if not isinstance(item, str):
            continue
        word = item.strip()
        if word:
            words.append(word)

    return words


def normalize_filename_word(word: str) -> str:
    # Normalize umlauts only for the local output filename.
    return word.strip().translate(UMLAUT_FILENAME_TRANSLATION)


def normalize_for_match(value: str) -> str:
    normalized = value.casefold().translate(MATCH_TRANSLATION)
    return NON_ALPHANUMERIC_PATTERN.sub("", normalized)


def strip_file_namespace(title: str) -> str:
    if title.startswith("File:"):
        return title.split(":", 1)[1]
    return title


def select_best_audio_filename(candidates: list[str], word: str) -> str | None:
    if not candidates:
        return None

    target = normalize_for_match(word)
    ranked_candidates: list[tuple[tuple[int, int, int], str]] = []

    for candidate in candidates:
        stem = Path(candidate).stem
        normalized_full = normalize_for_match(stem)
        normalized_without_prefix = normalize_for_match(
            GERMAN_AUDIO_PREFIX_PATTERN.sub("", stem)
        )

        if normalized_without_prefix == target:
            match_rank = 4
        elif normalized_full == target:
            match_rank = 3
        elif normalized_without_prefix.startswith(target) or normalized_full.startswith(target):
            match_rank = 2
        elif target and (target in normalized_without_prefix or target in normalized_full):
            match_rank = 1
        else:
            match_rank = 0

        comparison_value = normalized_without_prefix or normalized_full
        ranked_candidates.append(
            (
                (
                    match_rank,
                    -abs(len(comparison_value) - len(target)),
                    -len(comparison_value),
                ),
                candidate,
            )
        )

    ranked_candidates.sort(key=lambda item: item[0], reverse=True)
    return ranked_candidates[0][1]


def extract_audio_filename(payload: dict[str, Any], word: str) -> str | None:
    # Pull .ogg file titles from the Wiktionary query response.
    pages = payload.get("query", {}).get("pages", {})
    candidates: list[str] = []

    for page in pages.values():
        for image in page.get("images", []) or []:
            title = image.get("title")
            if not isinstance(title, str):
                continue
            filename = strip_file_namespace(title)
            if filename.lower().endswith(".ogg"):
                candidates.append(filename)

    unique_candidates = list(dict.fromkeys(candidates))
    return select_best_audio_filename(unique_candidates, word)


def build_commons_download_url(filename: str) -> str:
    # Build the Wikimedia Commons file URL from the hashed upload path.
    normalized_filename = filename.replace(" ", "_")
    digest = hashlib.md5(normalized_filename.encode("utf-8")).hexdigest()
    encoded_filename = quote(normalized_filename, safe="")
    return (
        f"{COMMONS_UPLOAD_BASE_URL}/{digest[0]}/{digest[:2]}/{encoded_filename}"
    )


def ensure_database(connection: sqlite3.Connection) -> None:
    # Create the vocabulary table once before processing words.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS vocabulary (
            word TEXT PRIMARY KEY,
            audio_path TEXT,
            has_audio BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )
    connection.commit()


def upsert_vocabulary_entry(
    connection: sqlite3.Connection,
    word: str,
    audio_path: str | None,
    has_audio: bool,
) -> None:
    connection.execute(
        """
        INSERT INTO vocabulary (word, audio_path, has_audio)
        VALUES (?, ?, ?)
        ON CONFLICT(word) DO UPDATE SET
            audio_path = excluded.audio_path,
            has_audio = excluded.has_audio
        """,
        (word, audio_path, int(has_audio)),
    )
    connection.commit()


def request_wiktionary_audio_filename(
    session: requests.Session,
    word: str,
) -> str | None:
    # Query Wiktionary for media attached to the word page.
    try:
        response = session.get(
            WIKTIONARY_API_URL,
            params={
                "action": "query",
                "titles": word,
                "prop": "images",
                "format": "json",
                "redirects": 1,
                "imlimit": "max",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return extract_audio_filename(payload, word)
    finally:
        time.sleep(REQUEST_DELAY_SECONDS)


def download_audio_file(
    session: requests.Session,
    download_url: str,
    destination_path: Path,
) -> None:
    # Download the audio file from Wikimedia Commons as binary data.
    try:
        with session.get(
            download_url,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            response.raise_for_status()
            with destination_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
    except Exception:
        if destination_path.exists():
            destination_path.unlink()
        raise
    finally:
        time.sleep(REQUEST_DELAY_SECONDS)


def write_word_list(path: Path, words: list[str]) -> None:
    path.write_text("\n".join(words) + ("\n" if words else ""), encoding="utf-8")


def process_words(repo_root: Path) -> int:
    # Resolve the fixed project paths relative to the repository root.
    words_path = repo_root / "words.yaml"
    audio_directory = repo_root / "audio" / "de"
    missing_path = repo_root / "missing.txt"
    success_path = repo_root / "success.txt"
    database_path = repo_root / "words.db"

    audio_directory.mkdir(parents=True, exist_ok=True)

    words = load_words(words_path)
    connection = sqlite3.connect(database_path)
    ensure_database(connection)

    success_words: list[str] = []
    missing_words: list[str] = []

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        for word in words:
            filename = f"{normalize_filename_word(word)}.ogg"
            relative_audio_path = Path("audio") / "de" / filename
            absolute_audio_path = repo_root / relative_audio_path

            if absolute_audio_path.exists():
                upsert_vocabulary_entry(connection, word, str(relative_audio_path), True)
                success_words.append(word)
                print(f"[SKIP]    {word} → {relative_audio_path} (already exists)")
                continue

            try:
                audio_filename = request_wiktionary_audio_filename(session, word)
            except (requests.RequestException, ValueError) as error:
                upsert_vocabulary_entry(connection, word, None, False)
                missing_words.append(word)
                print(f"[ERROR]   {word} → lookup failed: {error}")
                continue

            if audio_filename is None:
                upsert_vocabulary_entry(connection, word, None, False)
                missing_words.append(word)
                print(f"[MISSING] {word} → no audio found, logged to missing.txt")
                continue

            download_url = build_commons_download_url(audio_filename)

            try:
                download_audio_file(session, download_url, absolute_audio_path)
            except (requests.RequestException, OSError) as error:
                upsert_vocabulary_entry(connection, word, None, False)
                missing_words.append(word)
                print(f"[ERROR]   {word} → download failed: {error}")
                continue

            upsert_vocabulary_entry(connection, word, str(relative_audio_path), True)
            success_words.append(word)
            print(f"[OK]      {word} → {relative_audio_path}")
    finally:
        session.close()
        connection.close()

    # Persist the run summary files after processing every word.
    write_word_list(success_path, success_words)
    write_word_list(missing_path, missing_words)
    return 0


def main() -> int:
    # Run the downloader and report fatal configuration issues cleanly.
    try:
        return process_words(get_repo_root())
    except (FileNotFoundError, ValueError, sqlite3.DatabaseError, OSError) as error:
        print(f"[ERROR]   {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
